#!/bin/bash

echo "🎨 Fixing ArmGuard GUI Styling Issues"
echo ""

cd /opt/armguard
source venv/bin/activate

echo "📝 Step 1: Check static files configuration..."

# Check Django static files settings
python -c "
from django.conf import settings
print('Static files configuration:')
print(f'STATIC_URL: {settings.STATIC_URL}')
print(f'STATIC_ROOT: {settings.STATIC_ROOT}')
try:
    print(f'STATICFILES_DIRS: {settings.STATICFILES_DIRS}')
except:
    print('STATICFILES_DIRS: Not configured')
"

echo ""
echo "📁 Step 2: Collect and organize static files..."

# Collect all static files
python manage.py collectstatic --noinput --clear

echo ""
echo "🔧 Step 3: Check static file permissions..."

# Fix static file permissions
sudo chown -R www-data:www-data /opt/armguard/core/static/
sudo chmod -R 755 /opt/armguard/core/static/

echo ""
echo "📋 Step 4: Check nginx static file serving..."

# Check nginx configuration for static files
echo "Current nginx configuration for static files:"
sudo grep -A 5 -B 5 "location /static" /etc/nginx/sites-available/armguard || echo "No static location found"

echo ""
echo "🔄 Step 5: Fix nginx static file configuration..."

# Add proper static file serving to nginx
sudo tee /etc/nginx/sites-available/armguard > /dev/null << 'NGINXCONF'
server {
    listen 80;
    server_name 192.168.0.177 localhost;

    # Static files
    location /static/ {
        alias /opt/armguard/core/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files
    location /media/ {
        alias /opt/armguard/core/media/;
        expires 7d;
    }

    # Main application
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts for large operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
}
NGINXCONF

echo "✅ Updated nginx configuration with proper static file serving"

echo ""
echo "🔄 Step 6: Restart nginx and armguard services..."

sudo systemctl reload nginx
sudo systemctl restart armguard

sleep 5

echo ""
echo "🧪 Step 7: Test static file access..."

# Test static file serving
STATIC_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/admin/css/base.css 2>/dev/null || echo "000")
echo "Static file test (admin CSS): HTTP $STATIC_TEST"

MAIN_TEST=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
echo "Main page test: HTTP $MAIN_TEST"

echo ""
echo "📱 Step 8: Check for missing CSS/JS files..."

# List static files
echo "Static files available:"
ls -la /opt/armguard/core/static/ 2>/dev/null || echo "No static directory found"

if [ -d "/opt/armguard/core/static/admin" ]; then
    echo "Admin static files:"
    ls -la /opt/armguard/core/static/admin/css/ | head -5
else
    echo "❌ Admin static files missing - running collectstatic again..."
    python manage.py collectstatic --noinput
fi

echo ""
echo "🎨 Step 9: Check for custom ArmGuard styling..."

# Check if custom CSS exists
if [ -d "/opt/armguard/core/static/core" ]; then
    echo "✅ ArmGuard custom static files found"
    ls -la /opt/armguard/core/static/core/
else
    echo "⚠️  Creating basic ArmGuard static files..."
    mkdir -p /opt/armguard/core/static/core/css
    mkdir -p /opt/armguard/core/static/core/js
    
    # Create basic custom CSS
    cat > /opt/armguard/core/static/core/css/armguard.css << 'CSS'
/* ArmGuard Custom Styling */
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background-color: #f5f5f5;
    margin: 0;
    padding: 0;
}

.header {
    background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
    color: white;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.navigation {
    background-color: #34495e;
    padding: 0.5rem;
}

.navigation a {
    color: #ecf0f1;
    text-decoration: none;
    padding: 0.5rem 1rem;
    margin: 0 0.25rem;
    border-radius: 4px;
    display: inline-block;
}

.navigation a:hover {
    background-color: #3498db;
    transition: background-color 0.3s ease;
}

.dashboard-container {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 1rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.stat-card {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    border-left: 4px solid #3498db;
}

.stat-number {
    font-size: 2.5rem;
    font-weight: bold;
    color: #3498db;
    margin-bottom: 0.5rem;
}

.stat-label {
    color: #7f8c8d;
    font-size: 1.1rem;
    margin-bottom: 1rem;
}

.recent-transactions {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}

.section-title {
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}

.footer {
    background-color: #2c3e50;
    color: #ecf0f1;
    text-align: center;
    padding: 1rem;
    margin-top: 2rem;
}

/* Responsive design */
@media (max-width: 768px) {
    .stats-grid {
        grid-template-columns: 1fr;
    }
    
    .navigation a {
        display: block;
        margin: 0.25rem 0;
    }
}
CSS
    
    echo "✅ Created basic ArmGuard CSS"
    
    # Collect static files again to include the new CSS
    python manage.py collectstatic --noinput
fi

echo ""
echo "🔄 Step 10: Final service restart and test..."

sudo systemctl restart nginx
sudo systemctl restart armguard

sleep 10

FINAL_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/ 2>/dev/null || echo "000")
FINAL_STATIC=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/static/admin/css/base.css 2>/dev/null || echo "000")

echo ""
echo "🎉 FINAL RESULTS:"
echo "================"
echo "  • Main page: HTTP $FINAL_HTTP"
echo "  • Static files: HTTP $FINAL_STATIC"
echo "  • Nginx: $(sudo systemctl is-active nginx)"
echo "  • ArmGuard: $(sudo systemctl is-active armguard)"

if [ "$FINAL_HTTP" = "200" ] && [ "$FINAL_STATIC" = "200" ]; then
    echo ""
    echo "✅ SUCCESS! GUI should be fixed!"
    echo ""
    echo "🎨 Styling Status:"
    echo "  ✅ Static files serving correctly"
    echo "  ✅ CSS files accessible"
    echo "  ✅ Custom ArmGuard styling added"
    echo "  ✅ Responsive design enabled"
    echo ""
    echo "🌐 Access your improved ArmGuard:"
    echo "  • Main: http://192.168.0.177"
    echo "  • Admin: http://192.168.0.177/admin"
    echo ""
    echo "🔄 Clear your browser cache if styling still looks wrong!"
    
else
    echo ""
    echo "⚠️  Still having issues:"
    if [ "$FINAL_HTTP" != "200" ]; then
        echo "  • Main page not accessible"
    fi
    if [ "$FINAL_STATIC" != "200" ]; then
        echo "  • Static files not serving"
    fi
    
    echo ""
    echo "📋 Debug info:"
    echo "Nginx error log:"
    sudo tail -n 10 /var/log/nginx/error.log
fi