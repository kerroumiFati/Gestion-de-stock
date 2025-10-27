"""
Special view to create the first admin user
This should be disabled after first use for security
"""
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os

@csrf_exempt
def create_first_admin(request):
    """
    Create the first admin user
    URL: /create-first-admin/
    Method: POST
    Parameters: username, email, password

    IMPORTANT: This endpoint should be disabled after creating the first admin!
    """
    # Check if admin already exists
    if User.objects.filter(is_superuser=True).exists():
        return JsonResponse({
            'error': 'An admin user already exists. This endpoint is disabled for security.'
        }, status=403)

    if request.method == 'POST':
        # Get credentials from POST data
        username = request.POST.get('username', 'admin')
        email = request.POST.get('email', 'admin@gestionstock.com')
        password = request.POST.get('password')

        if not password:
            return JsonResponse({
                'error': 'Password is required'
            }, status=400)

        # Create superuser
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            return JsonResponse({
                'success': True,
                'message': f'Admin user "{username}" created successfully!',
                'username': username,
                'email': email
            })
        except Exception as e:
            return JsonResponse({
                'error': f'Error creating admin: {str(e)}'
            }, status=500)

    # GET request - show simple form
    return HttpResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create First Admin</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 500px;
                margin: 50px auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .form-container {
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                margin-bottom: 20px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }
            input {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                box-sizing: border-box;
            }
            button {
                width: 100%;
                padding: 12px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 10px;
            }
            button:hover {
                background: #0056b3;
            }
            .warning {
                background: #fff3cd;
                border: 1px solid #ffc107;
                padding: 15px;
                border-radius: 4px;
                margin-bottom: 20px;
                color: #856404;
            }
        </style>
    </head>
    <body>
        <div class="form-container">
            <h1>Create First Admin User</h1>
            <div class="warning">
                <strong>Warning:</strong> This page creates the first admin user.
                After creating your admin, remove this URL from your routes for security.
            </div>
            <form method="POST">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" value="admin" required>
                </div>
                <div class="form-group">
                    <label for="email">Email:</label>
                    <input type="email" id="email" name="email" value="admin@gestionstock.com" required>
                </div>
                <div class="form-group">
                    <label for="password">Password:</label>
                    <input type="password" id="password" name="password" required
                           placeholder="Enter a strong password">
                </div>
                <button type="submit">Create Admin User</button>
            </form>
        </div>
    </body>
    </html>
    """)
