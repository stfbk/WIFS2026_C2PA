# WIFS2026_C2PA

Official implementation of our paper:

> **Enhanced image forensics through partial C2PA-based provenance information**  
> *Riccardo Ziglio, Eleonora Marchesini, Andrea Montibeller, Giulia Boato, Silvio Ranise, Cecilia Pasquini*  
> Accepted to IEEE Workshop on Information Forensics and Security 2026

**CODE** available soon.

**Dataset** available [here](https://fbk-my.sharepoint.com/:f:/g/personal/rziglio_fbk_eu/IgApuiOTiMY3Q4kiRhrejUUMAXm7B8dj7SBDIqm4M2KzCas?e=5LWuwA).

**Model weights** available [here](https://fbk-my.sharepoint.com/:f:/g/personal/rziglio_fbk_eu/IgCiQOCr3hxKSIPfO6eEDcXTAVV_Mg-0xuMD9EMdHvYzEwA?e=fYNIlQ).

controllare che i modelli siano salvati con i path corretti: detectors/<MODEL>/checkpoint/<RUN>/weights/best.pt
dove <RUN> dipende dal modello>

- R50-* backbones hanno unfreeze_l4_ft
- CLIP-D

## Pipeline

![pipeline-image](assets/pipeline.drawio.png)

TODO: add scipts for each portion of the pipeline

- CC-based reconstruction
  - preset-analysis
  - cn-mapper

- Reconstruction-aware detector adaptation (SDA)
  - code from TB for FT models

- add general README describing the repo and specific README for each subfolder
  - make sure to add also notes where to add dataset or model weights

- add utils scripts for the generation of the trn/tst splits for TF_clean and TF_social datasets (briefly explain selection strategy)
  - basically there was no 1 to 1 matching images from PRE to social splits. So all matching images were selected and then new ones were randomly taken from the TB social dataset to reach the correct number of images per each category as in the original PRE split.
  