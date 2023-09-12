In the context of autonomous driving, the existing semantic segmentation concept strongly supports on-road driving where hard inter-class boundaries are enforced and objects can be categorized based on their visible structures with high confidence. Due to the well-structured nature of typical on-road scenes, current road extraction processes are largely successful and most types of vehicles are able to traverse through the area that is detected as road. However, the off-road driving domain has many additional uncertainties such as uneven terrain structure, positive and negative obstacles, ditches, quagmires, hidden objects, etc. making it very unstructured. Traversing through such unstructured area is constrained by a vehicle’s type and its capability. Therefore, an alternative approach to segmentation of the off-road driving trail is required that supports consideration of the vehicle type in a way that is not considered in state-of-the-art on-road segmentation approaches.

To overcome this limitation and facilitate the path extraction in the off-road driving domain, authors propose traversability concept and corresponding dataset which is based on the notion that the driving trails should be finely resolved into different sub-trails and areas corresponding to the capability of different vehicle classes in order to achieve safe traversal. Based on this, we consider three different classes of vehicles (_sedan_, _pickup_, and _off-road_) and label the images corresponding to the traversing capability of those vehicles.

![Vehicles classes](https://i.ibb.co/dbHnHqM/tang2-3154419-large.gif)

So the proposed dataset facilitates the segmentation of off-road driving trail into three regions based on the nature of the driving area and vehicle capability: **_brown_field_**, **_main_trail_**, **_power_line_**.

![Proving Ground Map](https://i.ibb.co/DgGpKS3/tang3-3154419-large.gif)

Authors call this dataset as _CaT_ (CAVS Traversability, where CAVS stands for Center for Advanced Vehicular Systems).
