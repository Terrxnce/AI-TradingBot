@echo off
echo 🤖 Starting D.E.V.I Trading Bot GUI...
echo 📍 Access URL will be shown below
echo 🔑 Default password: devi2025beta
echo ==================================================

python -m streamlit run streamlit_app.py --server.port 8501 --server.headless true
pause