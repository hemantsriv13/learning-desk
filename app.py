"""Learning Desk entry point. Run with:  streamlit run app.py"""

import streamlit as st

from learning_desk import db
from learning_desk.ui import common, other_pages, session_page, library, today

st.set_page_config(page_title="Learning Desk", page_icon=":material/menu_book:", layout="centered")
db.init_db()

common.PAGES.update(
    home=st.Page(today.today, title="Today", icon=":material/home:", default=True),
    library=st.Page(library.render, title="Library", icon=":material/local_library:", url_path="library"),
    notebook=st.Page(today.notebook, title="Notebook", icon=":material/menu_book:", url_path="notebook"),
    session=st.Page(session_page.render, title="Session", icon=":material/edit_note:", url_path="session", visibility="hidden"),
    queue=st.Page(other_pages.queue, title="Queue", icon=":material/checklist:", url_path="queue"),
    search=st.Page(other_pages.search, title="Search & export", icon=":material/search:", url_path="search"),
    settings=st.Page(other_pages.settings, title="Settings & About", icon=":material/settings:",
                     url_path="settings"),
)

st.navigation({
    "Learn": [common.PAGES[k] for k in ("home", "library", "notebook")],
    "Notebook editor": [common.PAGES["session"]],
    "Tools": [common.PAGES[k] for k in ("queue", "search", "settings")],
}).run()
