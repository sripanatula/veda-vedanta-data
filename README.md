# Veda Vedanta - Processed Data Repository

This repository is the automated data processing and serving layer for the [vedavedanta.com](https://vedavedanta.com) website. It functions as the "headless CMS" or "data backend" in the project's Jamstack architecture.

It automatically processes raw verse files from the `veda-vedanta-raw` repository and transforms them into structured, machine-readable JSON.

## 🕉️ Purpose

The goal of this repository is to decouple the raw, human-edited text from the structured data needed by the public website. It creates a clean, version-controlled, and automated "single source of truth" for all website content.

This repository contains:
-   **Structured Data**: The `vv/data/` directory holds the generated JSON files (e.g., `name-052.json`).
-   **Manifests & Indexes**: The `vv/data/.../index.json` and `vv/manifests/` files contain summary data for the collections.
-   **Automation**: The `.github/workflows/` directory contains GitHub Actions that run the processing scripts.
-   **Scripts**: The `tools/` directory contains the Python scripts (`update_from_raw.py`) responsible for parsing the raw `.txt` files and generating the final JSON.

## Workflow

This repository's workflow is fully automated via GitHub Actions:

1.  **Trigger**: A GitHub Action is triggered by a push to the `main` branch of the `veda-vedanta-raw` repository.
2.  **Fetch**: The action checks out the latest content from `veda-vedanta-raw`.
3.  **Process**: The `tools/update_from_raw.py` script runs. It detects which raw files have changed.
4.  **Generate**: For each changed file (e.g., `name-052.txt`), the script generates a corresponding JSON file (`name-052.json`) and rebuilds the collection's `index.json`.
5.  **Commit**: The workflow commits the newly generated JSON files back to this `veda-vedanta-data` repository.

This final commit then triggers the deployment pipeline in the `vedavedanta-site` (public) repository, which rebuilds and deploys the website with the fresh data.

## Scripts

### `tools/update_from_raw.py`

This is the core processing script. It's responsible for:
-   Detecting changes in the raw content repository.
-   Parsing both `verse-NNN.txt` and `name-NNN.txt` files.
-   Generating individual JSON files, collection indexes, and high-level manifests.
-   Committing the results back to this repository.