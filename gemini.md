# Gemini Code Assist - Project Configuration

This file provides context to Gemini Code Assist about the `veda-vedanta-public` repository.

## Project Overview

This is the third and final stage of the Veda Vedanta content pipeline. This repository contains the public-facing website code (likely an Astro project), which is deployed to vedavedanta.com.

## Key Components

-   **`src/`**: The source code for the website, built with a static site generator.
-   **Content Consumption**: The site is designed to read structured JSON data from the `veda-vedanta-data` repository. This is implemented using a Git submodule.
-   **`.github/workflows/`**: Contains the deployment pipeline. A GitHub Action is triggered by changes in the `veda-vedanta-data` repo, which then builds this site and deploys it to a hosting provider like Vercel or Netlify.