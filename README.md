![Status](https://img.shields.io/badge/status-work_in_progress-yellow)

# KiCad Component Pipeline

A complete data pipeline and management tool for creating and maintaining a KiCad database library. It fetches component data from APIs, manages categorization, and links symbols and footprints to create fully-defined "atomic parts".

## 🌟 Features

-   **Automated Data Fetching**: Pulls rich component data from **Digi-Key** and **Mouser** APIs.
-   **Intelligent Symbol & Footprint Linking**: Automatically finds and suggests appropriate symbols and footprints for components. Supports both part-specific and generic library items.
-   **Interactive Assistants**: Includes helper scripts like `map-categories` to easily "teach" the system new supplier categories without writing SQL.
-   **Bulk Processing**: Ingests part numbers from **CSV**, **Excel (.xlsx)**, **ODS**, and **TXT** files to process entire BOMs at once.
-   **Database-Driven**: Uses a robust **PostgreSQL** database as a single source of truth for all component data.
-   **KiCad Integration**: Designed to work seamlessly with KiCad's **Database Library** feature, using a single `.kicad_dbl` configuration file.
-   **Powerful CLI**: A comprehensive Command-Line Interface for managing all aspects of the library lifecycle.

## ✅ Development Status

The core functionalities of this project are complete, and the application is **ready for use**. The system supports a full end-to-end workflow, from fetching new part data to linking all necessary library assets for use in KiCad.

## 🛠️ Tech Stack

-   **Language:** Python 3.10+
-   **Database:** PostgreSQL
-   **Primary Libraries:**
    -   `requests`: For API communication
    -   `psycopg2-binary`: For PostgreSQL connection
    -   `python-dotenv`: For managing environment variables
    -   `pandas`: For reading spreadsheet files
    -   `openpyxl`: For `.xlsx` file support
    -   `odfpy`: For `.ods` file support

## 🚀 Getting Started

### Prerequisites

-   Python 3.10 or higher
-   PostgreSQL Server
-   Git

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
    -   Copy the `.env.example` file to `.env`.
    -   Fill in your database credentials, API keys, and the absolute paths to your KiCad symbol/footprint library folders.

    ```bash
    cp .env.example .env
    ```

    **Example `.env` file:**
    ```env
    # --- PostgreSQL Database ---
    DB_HOST=localhost
    DB_PORT=5432
    DB_NAME=kicad_components
    DB_USER=postgres
    DB_PASSWORD=your_secure_password

    # --- Supplier API Keys ---
    DIGIKEY_CLIENT_ID=your_digikey_client_id
    DIGIKEY_CLIENT_SECRET=your_digikey_client_secret
    MOUSER_API_KEY=your_mouser_api_key

    # --- KiCad Library Paths (Absolute Paths Recommended) ---
    KICAD_SYMBOL_BASE_PATH="/path/to/your/kicad/symbols"
    KICAD_FOOTPRINT_BASE_PATH="/path/to/your/kicad/footprints"
    ```

## Usage

All commands are run from the project's root directory using the main CLI entry point.

### 1. `fetch`

Fetches component data from supplier APIs and populates the `components` table.

-   **Single Part:**
    ```bash
    python -m scripts.main fetch -p "PART_NUMBER"
    ```
-   **From a File (e.g., Excel BOM):**
    ```bash
    python -m scripts.main fetch --spreadsheet "path/to/bom.xlsx" --column "Part Number"
    ```

### 2. `map-categories`

Starts an interactive assistant to map unknown supplier categories to your internal categories.
  ```bash
  python -m scripts.main map-categories
  ```
### 3. `import-symbols`

Parses `.kicad_sym` library files and imports their contents into the `symbols` database catalog.

-   **Single File:**
  ```bash
  python -m scripts.main import-symbols --file "Device.kicad_sym"
  ```
-   **Entire Directory (Recursive):**

  ```bash
  python -m scripts.main import-symbols --directory "path/to/your/symbol/libraries"
  ```
### 4. `add-symbol`

Finds and links a symbol to a component in the database.

-   **Interactive (Single Part):**

  ```bash
  python -m scripts.main add-symbol -p "PART_NUMBER"
  ```
-   **Bulk (from File):**

  ```bash
  python -m scripts.main add-symbol --spreadsheet "path/to/bom.xlsx" --column "Part Number"
  ```
-   **Overwrite existing data:**

  ```bash
  python -m scripts.main add-symbol -p "PART_NUMBER" --force
  ```
### 5. `add-footprint`(Teach)

"Teaches" the system a new valid footprint for a part number by adding it to the `footprint_mappings` catalog.

  ```bash
  python -m scripts.main add-footprint -p "PART_NUMBER" -f "LibraryNickname:FootprintName"
  ```
### 6. `link-footprint` (Choose & Link)

Chooses from the approved catalog and links a footprint to a component.

  ```bash
  python -m scripts.main link-footprint -p "PART_NUMBER"
  ```
### 7. `scan-missing`

Scans the database to report which components are missing a symbol or footprint.

  ```bash
  python -m scripts.main scan-missing --symbol
  python -m scripts.main scan-missing --footprint
  ```
