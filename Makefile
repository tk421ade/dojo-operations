

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

clean:
	rm -rf venv

recreate: clean
	python -m venv venv
	./venv/bin/pip3 install -r requirements.txt