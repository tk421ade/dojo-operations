
# Deploy configuration — gitignored, create locally
-include .deploy.env

DEPLOY_HOST  ?=
DEPLOY_PATH  ?= /opt/dojo-operations

clean:
	rm -rf venv
	find . -name '*.pyc ' -delete

prepare:clean
	set -ex
	#virtualenv venv -p /usr/bin/python3
	python3 -m venv venv
	venv/bin/pip3 install -r requirements.txt
	#venv/bin/pip install .


migrations:
	./venv/bin/python3 manage.py makemigrations shodan
	./venv/bin/python3 manage.py makemigrations financial
	./venv/bin/python3 manage.py makemigrations dojoconf
	./venv/bin/python3 manage.py migrate

migrate:
	./venv/bin/python3 manage.py migrate


create_test_admin_user:
	./venv/bin/python3 manage.py createsuperuser --username admin --email admin@example.com

database_reset:
	./venv/bin/python3 manage.py flush

freeze:
	./venv/bin/pip3 freeze > requirements.txt

recreate: clean
	python -m venv venv
	./venv/bin/pip3 install -r requirements.txt

reset-database: database_reset
	find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
	find . -path "*/migrations/*.pyc"  -delete
	./venv/bin/pip3 install --upgrade --force-reinstall  Django==5.2

collectstatic:
	./venv/bin/python3 manage.py collectstatic --no-input

create_secret_key:
	./venv/bin/python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

update:
	git pull

restart_gunicorn:
	systemctl restart gunicorn.service

update_project: update prepare collectstatic restart_gunicorn

db-backup:
	mkdir -p backups
	sudo -u postgres pg_dump shodan > backups/shodan_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Database backup saved to backups/"

deploy-local: db-backup update_project migrate restart_gunicorn

deploy:
	@if [ -z "$(DEPLOY_HOST)" ]; then \
		echo "ERROR: DEPLOY_HOST is not set."; \
		echo "Create .deploy.env with:  DEPLOY_HOST=user@hostname"; \
		echo "Or run:  DEPLOY_HOST=user@hostname make deploy"; \
		exit 1; \
	fi
	@echo "Deploying to $(DEPLOY_HOST):$(DEPLOY_PATH)..."
	ssh $(DEPLOY_HOST) "cd $(DEPLOY_PATH) && make deploy-local"
	@echo "Deployment complete."

clearsessions:
	./venv/bin/python manage.py clearsessions

create_fixtures:
	# auth
	./venv/bin/python manage.py dumpdata auth.group > fixtures/auth_groups_data.json
	./venv/bin/python manage.py dumpdata auth > fixtures/auth_test_data.json

	# dojo conf
	./venv/bin/python manage.py dumpdata dojoconf     >  fixtures/dojoconf_test_data.json

load_prod_fixtures:
	./venv/bin/python manage.py loaddata fixtures/auth_groups_data.json

load_dev_fixtures: load_prod_fixtures
	./venv/bin/python manage.py loaddata fixtures/auth_test_data.json
	./venv/bin/python manage.py loaddata fixtures/dojoconf_test_data.json

matrix_test:
	./venv/bin/python3 manage.py send_matrix_test
