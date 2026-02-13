run:
	uvicorn backend.app:app --reload

streamlit:
	streamlit run frontend/streamlit_app.py

docker-build:
	docker-compose build

docker-run:
	docker-compose up
