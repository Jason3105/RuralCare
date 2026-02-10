#!/bin/bash
# Insurance_SIP Setup Commands
# Copy and paste these commands one by one in your terminal

echo "================================================"
echo "  Insurance_SIP - Setup & Installation"
echo "================================================"
echo ""

# Step 1: Navigate to project directory
echo "Step 1: Navigating to project directory..."
cd "C:\Users\Ashley\OneDrive\Documents\The xDEVS\Rural-Health-Support"

# Step 2: Activate virtual environment (if using)
echo ""
echo "Step 2: Activating virtual environment..."
# Uncomment the appropriate line:
# .\venv\Scripts\activate          # Windows
# source venv/bin/activate         # Linux/Mac

# Step 3: Create migrations
echo ""
echo "Step 3: Creating migrations for Insurance_SIP..."
python manage.py makemigrations Insurance_SIP

# Step 4: Run migrations
echo ""
echo "Step 4: Running migrations..."
python manage.py migrate

# Step 5: Create superuser (if not exists)
echo ""
echo "Step 5: Creating superuser..."
echo "Skip this if you already have a superuser account"
# python manage.py createsuperuser

# Step 6: Collect static files (if needed)
echo ""
echo "Step 6: Collecting static files..."
# python manage.py collectstatic --noinput

# Step 7: Start development server
echo ""
echo "Step 7: Starting development server..."
echo "================================================"
echo "  Server will start at: http://127.0.0.1:8000"
echo "  Insurance App: http://127.0.0.1:8000/insurance/"
echo "  Admin Panel: http://127.0.0.1:8000/admin/"
echo "================================================"
python manage.py runserver

# Done!
echo ""
echo "Setup complete! 🎉"
