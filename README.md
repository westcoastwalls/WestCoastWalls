# WestCoastWalls - Project Management System

## Local Files Setup

Save these files to `C:\Users\bmaryniuk\Desktop\WestCoastWalls`:

```
WestCoastWalls/
├── app.py
├── requirements.txt
├── render.yaml
├── templates/
│   ├── index.html
│   └── login.html
└── README.md
```

## Render Deployment Steps

### 1. Push to GitHub
```bash
cd C:\Users\bmaryniuk\Desktop\WestCoastWalls
git init
git add .
git commit -m "Initial WestCoastWalls app"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 2. Deploy on Render
1. Go to https://render.com and sign in
2. Click "New +" → "Blueprint"
3. Connect your GitHub repository
4. Render will detect `render.yaml` automatically
5. Click "Apply" to deploy both the web service and database

### 3. Initialize Database
Once deployed, visit: `https://your-app-name.onrender.com/init-db`

This creates the database tables and default admin user.

### 4. Login
- URL: `https://your-app-name.onrender.com`
- Username: `admin`
- Password: `admin123`

## Features
- ✅ User authentication
- ✅ Project CRUD operations
- ✅ Status tracking (Quoted, Approved, In Progress, Completed)
- ✅ Quote vs actual cost tracking
- ✅ PostgreSQL database
- ✅ Responsive design

## Default Credentials
**Username:** admin  
**Password:** admin123

⚠️ **Change these immediately after first login!**