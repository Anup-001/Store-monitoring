# Store Monitoring API

## Overview
This project provides backend APIs for monitoring restaurant store uptime and downtime based on business hours and periodic status polling. It generates reports for restaurant owners to analyze store performance.

## Features
- Ingests store status, business hours, and timezone data from CSV files
- Stores data in a database for dynamic querying
- Provides two main API endpoints:
  - `/trigger_report`: Triggers report generation and returns a `report_id`
  - `/get_report`: Returns the status of the report or the generated CSV file
- Calculates uptime/downtime for last hour, day, and week, considering only business hours
- Handles missing data and timezones with sensible defaults

## Setup
1. Clone the repository:
   ```sh
   git clone https://github.com/Anup-001/Store-monitoring.git
   cd Store-monitoring
   ```
2. Create and activate a Python virtual environment:
   ```sh
   python -m venv venv
   # Windows:
   .\venv\Scripts\Activate.ps1
   # Linux/Mac:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```
4. Start the API server:
   ```sh
   uvicorn app.main:app --reload
   ```

## Usage
- Use `/trigger_report` (POST) to start report generation. Example response:
  ```json
  { "report_id": "<uuid>" }
  ```
- Use `/get_report?report_id=<uuid>` (GET) to poll for report status or download the CSV when complete.

## Sample Output
Sample report CSVs are available in the `reports/` folder. Each file is named by its `report_id`.

## Improvements & Ideas
- Add authentication for API endpoints
- Add pagination and filtering for large reports
- Improve error handling and logging
- Add unit and integration tests for all endpoints
- Dockerize the application for easier deployment

## Demo
A demo video showing the full flow is available [here](#) (add your Loom/YouTube link).

## License
This project is licensed under the MIT License.
