# Veda Vedanta - Public Website

This repository contains the source code for the public-facing website, [vedavedanta.com](https://vedavedanta.com).

## 🕉️ Purpose

The purpose of this repository is to build and deploy the Veda Vedanta website. It consumes structured JSON data from the `veda-vedanta-data` repository and renders it into a fast, user-friendly, and statically-generated website.

This repository contains:
-   **Website Source Code**: The `src/` directory contains the application code (e.g., Astro, Svelte, or React components, pages, and layouts).
-   **Deployment Configuration**: Files related to the deployment environment (e.g., `astro.config.mjs`, `vercel.json`, or `netlify.toml`).
-   **CI/CD Pipeline**: The `.github/workflows/` directory contains the GitHub Action responsible for building and deploying the site.

## Technology Stack

*(Note: You can update this section with your specific framework)*

-   **Framework**: Astro (or Next.js, SvelteKit, etc.)
-   **Content Source**: `veda-vedanta-data` repository (via a Git submodule or a fetch script during build).
-   **Hosting**: Vercel / Netlify / GitHub Pages

## Workflow

The deployment workflow is fully automated:

1.  **Trigger**: A GitHub Action in this repository is triggered by a push to the `main` branch of the `veda-vedanta-data` repository.
2.  **Fetch Content**: The workflow ensures it has the latest JSON content. This is often done by updating a Git submodule that points to `veda-vedanta-data`.
3.  **Build**: The static site generator (e.g., `npm run build`) is run. It reads the JSON files and generates the final HTML, CSS, and JavaScript for the entire site.
4.  **Deploy**: The built assets (typically in a `dist/` or `.output/` folder) are pushed to the hosting provider.

## Local Development

1.  Clone this repository.
2.  Make sure the content submodule is initialized and updated: `git submodule update --init --remote`.
3.  Install dependencies: `npm install`.
4.  Run the development server: `npm run dev`.