# OnePiece Self-Hosted Scraper

A fully functional, self-hosted scraper for downloading and managing OnePiece manga. This system includes a web interface accessible at `localhost:1234`.

---

## Requirements

- **Storage**: 10GB of storage for templates and downloaded images.
- **RAM**: Sufficient memory to handle the scraper and web interface.
- **CPU**: Adequate processing power for smooth operation.
- **Internet**: Stable internet connection for downloading ~10GB of images.
- **Docker and Docker Compose**: Ensure Docker and Docker Compose are installed on your system.

### Docker Installation Guides
- **Linux**: [Install Docker on Linux](https://docs.docker.com/desktop/setup/install/linux/)
- **Windows**: [Install Docker on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)
- **Mac**: [Install Docker on Mac](https://docs.docker.com/desktop/setup/install/mac-install/)

---

## !!Warning!!
This scraper will download approximately **10GB of images** from a website. The process may take a significant amount of time, so ensure you run it beforehand.

---

## System Overview

The system consists of two Docker containers:
1. **Controller**: Responsible for setting up, downloading, and keeping the manga up to date.
2. **UI**: Provides a web interface for accessing the downloaded content.

---

## Setup Instructions

1. Clone this repository to your local machine.
2. Navigate to the repository directory.
3. Start the setup by running the following command:

   ```bash
   docker compose up -d --build
