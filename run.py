from app import app

# Run the application
if __name__ == '__main__':
    # Port 5001 because 5000 was giving errors on Windows
    app.run(host='localhost', port=5001, debug=True)
