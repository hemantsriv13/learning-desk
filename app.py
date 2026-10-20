"""Learning Desk entry point. Run with:  streamlit run app.py"""

import streamlit as st

from learning_desk import db
from learning_desk.ui import common, other_pages, session_page

st.set_page_config(page_title="Learning Desk", page_icon=":material/menu_book:", layout="wide")
db.init_db()

common.PAGES.update(
    home=st.Page(other_pages.home, title="Home", icon=":material/home:", default=True),
    session=st.Page(session_page.render, title="Session", icon=":material/edit_note:", url_path="session"),
    queue=st.Page(other_pages.queue, title="Queue", icon=":material/checklist:", url_path="queue"),
    search=st.Page(other_pages.search, title="Search & export", icon=":material/search:", url_path="search"),
    settings=st.Page(other_pages.settings, title="Settings & About", icon=":material/settings:",
                     url_path="settings"),
)

st.navigation(list(common.PAGES.values())).run()
