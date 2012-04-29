The Wiki Toolset
================

EarwigBot's answer to the `Pywikipedia framework`_ is the Wiki Toolset
(``earwigbot.wiki``), which you will mainly access through ``bot.wiki``.

``bot.wiki`` provides three methods for the management of Sites -
``get_site()``, ``add_site()``, and ``remove_site()``. Sites are objects that
simply represent a MediaWiki site. A single instance of EarwigBot (i.e. a
single *working directory*) is expected to relate to a single site or group of
sites using the same login info (like all WMF wikis with CentralAuth).

Load your default site (the one that you picked during setup) with
``site = bot.wiki.get_site()``.

Dealing with other sites
~~~~~~~~~~~~~~~~~~~~~~~~

*Skip this section if you're only working with one site.*

If a site is *already known to the bot* (meaning that it is stored in the
``sites.db`` file, which includes just your default wiki at first), you can
load a site with ``site = bot.wiki.get_site(name)``, where ``name`` might be
``"enwiki"`` or ``"frwiktionary"`` (you can also do
``site = bot.wiki.get_site(project="wikipedia", lang="en")``). Recall that not
giving any arguments to ``get_site()`` will return the default site.

``add_site()`` is used to add new sites to the sites database. It may be called
with similar arguments as ``get_site()``, but the difference is important.
``get_site()`` only needs enough information to identify the site in its
database, which is usually just its name; the database stores all other
necessary connection info. With ``add_site()``, you need to provide enough
connection info so the toolset can successfully access the site's API/SQL
databases and store that information for later. That might not be much; for
WMF wikis, you can usually use code like this::

    project, lang = "wikipedia", "es"
    try:
        site = bot.wiki.get_site(project=project, lang=lang)
    except earwigbot.SiteNotFoundError:
        # Load site info from http://es.wikipedia.org/w/api.php:
        site = bot.wiki.add_site(project=project, lang=lang)

This works because EarwigBot assumes that the URL for the site is
``"//{lang}.{project}.org"`` and the API is at ``/w/api.php``; this might
change if you're dealing with non-WMF wikis, where the code might look
something more like::

    project, lang = "mywiki", "it"
    try:
        site = bot.wiki.get_site(project=project, lang=lang)
    except earwigbot.SiteNotFoundError:
        Load site info from http://mysite.net/mywiki/it/s/api.php:
        base_url = "http://mysite.net/" + project + "/" + lang
        db_name = lang + project + "_p"
        sql = {host: "sql.mysite.net", db: db_name}
        site = bot.wiki.add_site(base_url=base_url, script_path="/s", sql=sql)

``remove_site()`` does the opposite of ``add_site()``: give it a site's name
or a project/lang pair like ``get_site()`` takes, and it'll remove that site
from the sites database.

Sites
~~~~~

``Site`` objects provide the following attributes:

- ``name``: the site's name (or "wikiid"), like ``"enwiki"``
- ``project``: the site's project name, like ``"wikipedia"``
- ``lang``: the site's language code, like ``"en"``
- ``domain``: the site's web domain, like ``"en.wikipedia.org"``

and the following methods:

- ``api_query(**kwargs)``: does an API query with the given keyword arguments
  as params
- ``sql_query(query, params=(), ...)``: does an SQL query and yields its
  results (as a generator)
- ``get_replag()``: returns the estimated database replication lag (if we have
  the site's SQL connection info)
- ``namespace_id_to_name(id, all=False)``: given a namespace ID, returns the
  primary associated namespace name (or a list of all names when ``all`` is
  ``True``)
- ``namespace_name_to_id(name)``: given a namespace name, returns the
  associated namespace ID
- ``get_page(title, follow_redirects=False)``: returns a ``Page`` object for
  the given title (or a ``Category`` object if the page's namespace is
  "``Category:``")
- ``get_category(catname, follow_redirects=False)``: returns a ``Category``
  object for the given title (sans namespace)
- ``get_user(username)``: returns a ``User`` object for the given username

Pages (and Categories)
~~~~~~~~~~~~~~~~~~~~~~

Create ``Page`` objects with ``site.get_page(title)``,
``page.toggle_talk()``, ``user.get_userpage()``, or ``user.get_talkpage()``.
They provide the following attributes:

- ``title``: the page's title, or pagename
- ``exists``: whether the page exists
- ``pageid``: an integer ID representing the page
- ``url``: the page's URL
- ``namespace``: the page's namespace as an integer
- ``protection``: the page's current protection status
- ``is_talkpage``: ``True`` if the page is a talkpage, else ``False``
- ``is_redirect``: ``True`` if the page is a redirect, else ``False``

and the following methods:

- ``reload()``: forcibly reload the page's attributes (emphasis on *reload* -
  this is only necessary if there is reason to believe they have changed)
- ``toggle_talk(...)``: returns a content page's talk page, or vice versa
- ``get()``: returns page content
- ``get_redirect_target()``: if the page is a redirect, returns its destination
- ``get_creator()``: returns a ``User`` object representing the first user to
  edit the page
- ``edit(text, summary, minor=False, bot=True, force=False)``: replaces the
  page's content with ``text`` or creates a new page
- ``add_section(text, title, minor=False, bot=True, force=False)``: adds a new
  section named ``title`` at the bottom of the page
- ``copyvio_check(...)``: checks the page for copyright violations
- ``copyvio_compare(url, ...)``: checks the page like ``copyvio_check()``, but
  against a specific URL

Additionally, ``Category`` objects (created with ``site.get_category(name)`` or
``site.get_page(title)`` where ``title`` is in the ``Category:`` namespace)
provide the following additional method:

- ``get_members(use_sql=False, limit=None)``: returns a list of page titles in
  the category (limit is ``50`` by default if using the API)

Users
~~~~~

Create ``User`` objects with ``site.get_user(name)`` or
``page.get_creator()``. They provide the following attributes:

- ``name``: the user's username
- ``exists``: ``True`` if the user exists, or ``False`` if they do not
- ``userid``: an integer ID representing the user
- ``blockinfo``: information about any current blocks on the user (``False`` if
  no block, or a dict of ``{"by": blocking_user, "reason": block_reason,
  "expiry": block_expire_time}``)
- ``groups``: a list of the user's groups
- ``rights``: a list of the user's rights
- ``editcount``: the number of edits made by the user
- ``registration``: the time the user registered as a ``time.struct_time``
- ``emailable``: ``True`` if you can email the user, ``False`` if you cannot
- ``gender``: the user's gender (``"male"``, ``"female"``, or ``"unknown"``)

and the following methods:

- ``reload()``: forcibly reload the user's attributes (emphasis on *reload* -
  this is only necessary if there is reason to believe they have changed)
- ``get_userpage()``: returns a ``Page`` object representing the user's
  userpage
- ``get_talkpage()``: returns a ``Page`` object representing the user's
  talkpage

Additional features
~~~~~~~~~~~~~~~~~~~

Not all aspects of the toolset are covered here. Explore `its code and
docstrings`_ to learn how to use it in a more hands-on fashion. For reference,
``bot.wiki`` is an instance of ``earwigbot.wiki.SitesDB`` tied to the
``sites.db`` file in the bot's working directory.

.. _Pywikipedia framework:   http://pywikipediabot.sourceforge.net/
.. _its code and docstrings: https://github.com/earwig/earwigbot/tree/develop/earwigbot/wiki
