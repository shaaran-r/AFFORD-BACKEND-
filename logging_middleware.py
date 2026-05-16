import time
from functools import wraps
from flask import Flask, request, g

app = Flask(__name__)

def logging_middleware(f):
    """
    Middleware to log request details: Method, Path, and Response Time.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        g.start_time = time.time()
        response = f(*args, **kwargs)
        
        # Calculate response time in milliseconds
        response_time = (time.time() - g.start_time) * 1000
        
        # Log the details
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {request.method} {request.path} - {response_time:.2f}ms")
        
        return response
    return decorated_function

@app.route('/test')
@logging_middleware
def test_route():
    time.sleep(0.1) # Simulate some processing time
    return "Logging Middleware Test Successful"

if __name__ == "__main__":
    # This is a demonstration of how the middleware would be used in a Flask app.
    # In a real scenario, this would be part of a larger backend application.
    print("Starting Flask app with Logging Middleware...")
    app.run(port=5000)
