## Populating the Database with Fake Data

To populate the database with fake data for testing purposes, follow these steps:

1. **Install Dependencies**: Ensure you have the required packages installed. You can do this by running:

   ```bash
   poetry add sqlalchemy psycopg2 faker
   ```

2. **Set Up Database Connection**: Make sure your database is running and update the `DATABASE_URL` in the `seed_data.py` script with your database credentials.

3. **Run the Script**: Execute the script to populate the database with fake data. You can run the script with:

   ```bash
   python web_app/db/seed_data.py
   ```

4. **Verify Data**: After running the script, you can check your database to ensure that the fake data has been inserted correctly.
