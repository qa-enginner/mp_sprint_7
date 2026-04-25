
chmod +x /Users/av_bakharev/Dev/Auth_sprint_2/init-scripts/01-create-databases.sh
chmod +x /Users/av_bakharev/Dev/Auth_sprint_2/init-scripts/02-load-dump.sh

cd services/admin-panel/app && python manage.py startapp users


docker exec -ti admin_panel python manage.py createsuperuser
