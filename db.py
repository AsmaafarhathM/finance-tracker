import os

import mysql.connector
from mysql.connector import Error


def get_connection():
    """
    Create and return a new MySQL connection.
    The caller is responsible for closing the connection.
    """

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "finance_tracker"),
        autocommit=False,
    )


def init_db():
    """
    Create required tables if they don't exist.

    Notes:
    - Tables use `Users` and `Records` names to match assignment wording.
    - `Records.user_id` references `Users.id`.
    """

    conn = None
    cur = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                role ENUM('admin','analyst','viewer') NOT NULL,
                status BOOLEAN NOT NULL DEFAULT TRUE
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Records (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                amount DECIMAL(18, 2) NOT NULL,
                type ENUM('income','expense') NOT NULL,
                category VARCHAR(255) NOT NULL,
                date DATE NOT NULL,
                note TEXT,
                CONSTRAINT fk_records_user
                    FOREIGN KEY (user_id) REFERENCES Users(id)
                    ON DELETE CASCADE,
                INDEX idx_records_user_id (user_id),
                INDEX idx_records_date (date)
            )
            """
        )

        conn.commit()
    except Error:
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

