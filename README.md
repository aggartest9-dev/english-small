
# Learning Management System (LMS)

A backend application for a Learning Management System built using Python, Django, Django REST Framework, and PostgreSQL. It provides REST APIs for managing users, courses, and assessments.

## Features

- User authentication
- Course management with CRUD operations
- Pagination and filtering
- MCQ-based assessments
- Fill-in-the-blank assessments
- RESTful API architecture
- API testing using Postman

## Tech Stack

- **Language:** Python
- **Framework:** Django
- **API Framework:** Django REST Framework
- **Database:** PostgreSQL
- **API Testing:** Postman

## Project Structure

```text
LMS/
├── manage.py
├── requirements.txt
├── config/
├── users/
├── courses/
├── assessments/
└── README.md
```

*Note: Update the project structure according to your actual repository.*

## Getting Started

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <your-project-folder>
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

**Windows**
```bash
venv\Scripts\activate
```

**Linux / macOS**
```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and configure your database and other required settings.

Example:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=localhost
DB_PORT=5432
```

Make sure your `.env` file is included in `.gitignore`.

### 5. Apply Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Run the Development Server

```bash
python manage.py runserver
```

The application will be available at:

```text
http://127.0.0.1:8000/
```

## API Testing

The APIs were tested using Postman to validate:

- Request and response handling
- HTTP status codes
- Authentication
- CRUD operations
- Pagination and filtering
- Assessment functionality

## Future Improvements

- Add automated API tests
- Improve role-based access control
- Add course progress tracking
- Deploy the application
- Integrate a frontend interface

## Author

**Kavya Aggarwal**
- [LinkedIn](https://www.linkedin.com/in/kavya-aggarwal-a4008a237/)
