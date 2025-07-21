# KiCad Component Pipeline

Automated data pipeline to populate a KiCad component database from supplier APIs.

## 🌟 Features

- Automated fetching of component data from Digi-Key and Mouser APIs.
- Stores component data in a centralized PostgreSQL database.
- Normalizes data structure for efficient querying and management.
- Generates a KiCad Database Library (`.kicad_dbl`) for direct integration.

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Database:** PostgreSQL
- **Primary Libraries:**
  - `requests`: For API communication
  - `psycopg2-binary`: For PostgreSQL connection

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- PostgreSQL Server
- Git

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/TektraSense/kicad-component-pipeline.git](https://github.com/TektraSense/kicad-component-pipeline.git)
    cd kicad-component-pipeline
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up environment variables:**
    - Copy the `.env.example` file to `.env`
    - Fill in your database credentials and API keys.
    ```bash
    cp .env.example .env
    ```

## Usage

To fetch a new component, run the main script:

```bash
python scripts/fetch_parts.py --part-number "NE555DR"
