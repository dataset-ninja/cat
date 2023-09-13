import os
import shutil
from urllib.parse import unquote, urlparse

import numpy as np
import supervisely as sly
from dataset_tools.convert import unpack_if_archive
from supervisely.io.fs import file_exists, get_file_name
from tqdm import tqdm

import src.settings as s


def download_dataset(teamfiles_dir: str) -> str:
    """Use it for large datasets to convert them on the instance"""
    api = sly.Api.from_env()
    team_id = sly.env.team_id()
    storage_dir = sly.app.get_data_dir()

    if isinstance(s.DOWNLOAD_ORIGINAL_URL, str):
        parsed_url = urlparse(s.DOWNLOAD_ORIGINAL_URL)
        file_name_with_ext = os.path.basename(parsed_url.path)
        file_name_with_ext = unquote(file_name_with_ext)

        sly.logger.info(f"Start unpacking archive '{file_name_with_ext}'...")
        local_path = os.path.join(storage_dir, file_name_with_ext)
        teamfiles_path = os.path.join(teamfiles_dir, file_name_with_ext)

        fsize = api.file.get_directory_size(team_id, teamfiles_dir)
        with tqdm(desc=f"Downloading '{file_name_with_ext}' to buffer...", total=fsize) as pbar:
            api.file.download(team_id, teamfiles_path, local_path, progress_cb=pbar)
        dataset_path = unpack_if_archive(local_path)

    if isinstance(s.DOWNLOAD_ORIGINAL_URL, dict):
        for file_name_with_ext, url in s.DOWNLOAD_ORIGINAL_URL.items():
            local_path = os.path.join(storage_dir, file_name_with_ext)
            teamfiles_path = os.path.join(teamfiles_dir, file_name_with_ext)

            if not os.path.exists(get_file_name(local_path)):
                fsize = api.file.get_directory_size(team_id, teamfiles_dir)
                with tqdm(
                    desc=f"Downloading '{file_name_with_ext}' to buffer...",
                    total=fsize,
                    unit="B",
                    unit_scale=True,
                ) as pbar:
                    api.file.download(team_id, teamfiles_path, local_path, progress_cb=pbar)

                sly.logger.info(f"Start unpacking archive '{file_name_with_ext}'...")
                unpack_if_archive(local_path)
            else:
                sly.logger.info(
                    f"Archive '{file_name_with_ext}' was already unpacked to '{os.path.join(storage_dir, get_file_name(file_name_with_ext))}'. Skipping..."
                )

        dataset_path = storage_dir
    return dataset_path


def count_files(path, extension):
    count = 0
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(extension):
                count += 1
    return count


def convert_and_upload_supervisely_project(
    api: sly.Api, workspace_id: int, project_name: str
) -> sly.ProjectInfo:
    dataset_path = "CAT"
    batch_size = 50

    classes = {27: "sedan", 56: "pickup", 245: "off road"}
    tag_names = ["brown_field", "main_trail", "power_line"]

    def replace_path(path):
        head = path
        tail = None
        file_name = os.path.basename(path).split(".")[0]
        prefix = "_pln_" if "pln" in file_name else "_"
        while tail != "imgs":
            head, tail = os.path.split(head)
        img_index = [str(n) for n in file_name if n.isdigit()]
        mask_name = f"mask{prefix}" + "".join(img_index) + ".png"
        return os.path.join(head, "masks", mask_name)

    def create_ann(image_path):
        labels = []
        image_np = sly.imaging.image.read(image_path)[:, :, 0]
        img_height = image_np.shape[0]
        img_wight = image_np.shape[1]
        mask_path = replace_path(image_path)
        for tag in tag_names:
            if tag in image_path.lower():
                tag_sly = [sly.Tag(tag_meta) for tag_meta in tag_metas if tag_meta.name == tag]
        if file_exists(mask_path):
            mask_np = sly.imaging.image.read(mask_path)[:, :, 0]
            if len(np.unique(mask_np)) != 1:
                uniq = np.unique(mask_np)
                for label in uniq:
                    if label != 0:
                        obj_mask = mask_np == label
                        curr_bitmap = sly.Bitmap(obj_mask)
                        obj_class = meta.get_obj_class(classes[label])
                        curr_label = sly.Label(curr_bitmap, obj_class)
                        labels.append(curr_label)
        return sly.Annotation(img_size=(img_height, img_wight), labels=labels, img_tags=tag_sly)

    obj_class_off = sly.ObjClass("off road", sly.Bitmap, [255, 0, 0])
    obj_class_pickup = sly.ObjClass("pickup", sly.Bitmap, [0, 128, 0])
    obj_class_sedan = sly.ObjClass("sedan", sly.Bitmap, [30, 144, 255])

    tag_metas = [sly.TagMeta(name, sly.TagValueType.NONE) for name in tag_names]

    project = api.project.create(workspace_id, project_name, change_name_if_conflict=True)
    meta = sly.ProjectMeta(
        obj_classes=[obj_class_off, obj_class_pickup, obj_class_sedan],
        tag_metas=tag_metas,
    )
    api.project.update_meta(project.id, meta.to_json())

    dataset_test = api.dataset.create(project.id, "test", change_name_if_conflict=True)
    dataset_train = api.dataset.create(project.id, "train", change_name_if_conflict=True)

    total_files = 0

    image_test = []
    image_train = []

    for r, d, f in os.walk(dataset_path):
        for dir in d:
            if "mixed" in r or dir == "mixed":
                continue
            if dir == "Test":
                img_folder = os.path.join(r, dir, "imgs")
                img_paths = [os.path.join(img_folder, file) for file in os.listdir(img_folder)]
                total_files += len(img_paths)
                image_test.extend(img_paths)
            elif dir == "Train":
                img_folder = os.path.join(r, dir, "imgs")
                img_paths = [os.path.join(img_folder, file) for file in os.listdir(img_folder)]
                total_files += len(img_paths)
                image_train.extend(img_paths)

    project_images = {"test": image_test, "train": image_train}
    progress = sly.Progress("Create datasets {}".format("test,train"), total_files)

    for ds in project_images:
        if ds == "test":
            dataset = dataset_test
        else:
            dataset = dataset_train
        img_paths = project_images[ds]
        for img_pathes_batch in sly.batched(img_paths, batch_size=batch_size):
            img_names_batch = [os.path.basename(img_path) for img_path in img_pathes_batch]
            img_infos = api.image.upload_paths(dataset.id, img_names_batch, img_pathes_batch)
            img_ids = [im_info.id for im_info in img_infos]
            anns_batch = [create_ann(image_path) for image_path in img_pathes_batch]
            api.annotation.upload_anns(img_ids, anns_batch)
            progress.iters_done_report(len(img_names_batch))

    return project
