

clean:
	rm -rf venv
	find . -name '*.pyc ' -delete

prepare:clean
	set -ex
	virtualenv venv -p /usr/bin/python3
	venv/bin/pip3 install -r requirements.txt
	#venv/bin/pip install .


migrations:
	./venv/bin/python3 manage.py makemigrations shodan
	./venv/bin/python3 manage.py makemigrations financial
	./venv/bin/python3 manage.py makemigrations dojoconf
	./venv/bin/python3 manage.py migrate


create_test_admin_user:
	./venv/bin/python3 manage.py createsuperuser --username username --email email@example.com

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
	./venv/bin/pip3 install --upgrade --force-reinstall  Django==5.1