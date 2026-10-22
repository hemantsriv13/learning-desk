"""Learning Desk entry point. Run with:  streamlit run app.py"""

import streamlit as st

from learning_desk import db
from learning_desk.ui import common, learn, library, other_pages, session_page, theme, today

st.set_page_config(page_title="Learning Desk", page_icon=":material/menu_book:", layout="wide")
theme.inject()
db.init_db()

common.PAGES.update(
    home=st.Page(today.today, title="Home", icon=":material/home:", default=True),
    explore=st.Page(learn.explore, title="Explore", icon=":material/explore:", url_path="explore"),
    library=st.Page(library.render, title="Library", icon=":material/local_library:", url_path="library"),
    notebook=st.Page(today.notebook, title="Notebook", icon=":material/menu_book:", url_path="notebook"),
    lesson=st.Page(learn.lesson_page, title="Lesson", icon=":material/school:", url_path="lesson",
                   visibility="hidden"),
    session=st.Page(session_page.render, title="Session", icon=":material/edit_note:", url_path="session", visibility="hidden"),
    queue=st.Page(other_pages.queue, title="Queue", icon=":material/checklist:", url_path="queue"),
    search=st.Page(other_pages.search, title="Search & export", icon=":material/search:", url_path="search"),
    settings=st.Page(other_pages.settings, title="Settings & About", icon=":material/settings:",
                     url_path="settings"),
)

st.navigation({
    "Learn": [common.PAGES[k] for k in ("home", "explore", "library", "notebook")],
    "Reading": [common.PAGES[k] for k in ("lesson", "session")],
    "Tools": [common.PAGES[k] for k in ("queue", "search", "settings")],
}).run()
