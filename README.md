# MLB Stats Tracker

![MLB Stats Tracker](https://i.imgur.com/NDy5sGI.mp4) An advanced, full-stack web application that provides daily MLB game schedules and detailed, real-time team and player statistics. The application is designed with a focus on performance, featuring background data fetching, a robust caching system, and a responsive front-end for both desktop and mobile viewing.

**Live Demo:** [MLB Stats](https://mlb.up.railway.app/)

## Features

* **Daily Game Schedule**: The homepage displays all games scheduled for the current day with team logos and start times in PST.
* **Detailed Game View**: Clicking on a game reveals a detailed breakdown of team and player statistics.  
* **Recent Performance Stats**: The batters show averages for the past 7, 10, 21 days. The pitchers show averages for the past 2 games, 3 games, and 4 games.
* **Backend Data Sorting**: Player tables are pre-sorted on the backend by the most relevant stat (At-Bats for batters, Games Started for pitchers).
* **Team Comparison**: A high-level overview comparing the recent performance of the two competing teams.
* **Responsive Design**: The user interface is fully responsive, offering a custom, compact table view on mobile devices for readability.
* **Favorites System**: Users can mark their favorite teams, which are displayed at the top of the homepage using a client-side session.

---

## Technical Details & Architecture

This project was built to showcase a full-stack skill set, moving beyond simple data scripts into a complete, deployed data product.

### Tech Stack

* **Backend**: Python, Flask, Gunicorn
* **Frontend**: HTML, CSS, JavaScript (no frameworks)
* **API**: [MLB Stats API](https://github.com/toddrob99/MLB-StatsAPI)
* **Deployment**: Railway, Git & GitHub

### Key Architectural Features

* **Refactored, Modular Structure**: The application is organized into logical modules (API handling, routes, background tasks, utilities), following best practices.
* **Performance Optimization**:
    * **Server-Side Caching**: Implemented with Flask-Caching to store API results for 24 hours, dramatically reducing load times and API usage.
    * **Parallel Data Fetching**: Uses a `ThreadPoolExecutor` to concurrently fetch stats for all players, significantly speeding up the data aggregation process.
* **Automated Background Tasks**:
    * **Cache Warming**: A background thread automatically pre-loads and caches all data for the day's games upon application startup.
    * **Daily Cache Refresh**: A scheduled task runs every morning at 6 AM PST to clear the previous day's data and warm the cache for the new day.
* **API Rate Limiting**: A custom `RateLimiter` class prevents the application from exceeding the API's request limits, ensuring stability and good API citizenship.

---

## Local Setup and Installation

To run this project locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone [GitHub](https://github.com/xgrantgamble/mlbStatAVGs.git)
    cd your-repo-name
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Mac/Linux
    python3 -m venv venv
    source venv/bin/activate

    # For Windows
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```bash
    flask run
    ```
    The application will be available at `http://127.0.0.1:5000`.

### Configuration

The application uses a `SECRET_KEY` for session management. For local development, a default key is provided. 
For production, this should be set as an environment variable.