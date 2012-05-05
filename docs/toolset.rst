The Wiki Toolset
================

EarwigBot's answer to the `Pywikipedia framework`_ is the Wiki Toolset
(:py:mod:`earwigbot.wiki`), which you will mainly access through
:py:attr:`bot.wiki <earwigbot.bot.Bot.wiki>`.

:py:attr:`bot.wiki <earwigbot.bot.Bot.wiki>` provides three methods for the
management of Sites - :py:meth:`~earwigbot.wiki.SiteDB.get_site`,
:py:meth:`~earwigbot.wiki.SiteDB.add_site`, and
:py:meth:`~earwigbot.wiki.SiteDB.remove_site`. Sites are objects that simply
represent a MediaWiki site. A single instance of EarwigBot (i.e. a single
*working directory*) is expected to relate to a single site or group of sites
using the same login info (like all WMF wikis with CentralAuth).

Load your default site (the one that you picked during setup) with
``site = bot.wiki.get_site()``.

Dealing with other sites
~~~~~~~~~~~~~~~~~~~~~~~~

*Skip this section if you're only working with one site.*

If a site is *already known to the bot* (meaning that it is stored in the
:file:`sites.db` file, which includes just your default wiki at first), you can
load a site with ``site = bot.wiki.get_site(name)``, where ``name`` might be
``"enwiki"`` or ``"frwiktionary"`` (you can also do
``site = bot.wiki.get_site(project="wikipedia", lang="en")``). Recall that not
giving any arguments to ``get_site()`` will return the default site.

:py:meth:`~earwigbot.wiki.SiteDB.add_site` is used to add new sites to the sites
database. It may be called with similar arguments as
:py:meth:`~earwigbot.wiki.SiteDB.get_site`, but the difference is important.
:py:meth:`~earwigbot.wiki.SiteDB.get_site` only needs enough information to
identify the site in its database, which is usually just its name; the database
stores all other necessary connection info. With
:py:meth:`~earwigbot.wiki.SiteDB.add_site`, you need to provide enough connection
info so the toolset can successfully access the site's API/SQL databases and
store that information for later. That might not be much; for WMF wikis, you
can usually use code like this::

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
        # Load site info from http://mysite.net/mywiki/it/s/api.php:
        base_url = "http://mysite.net/" + project + "/" + lang
        db_name = lang + project + "_p"
        sql = {host: "sql.mysite.net", db: db_name}
        site = bot.wiki.add_site(base_url=base_url, script_path="/s", sql=sql)

:py:meth:`~earwigbot.wiki.SiteDB.remove_site` does the opposite of
:py:meth:`~earwigbot.wiki.SiteDB.add_site`: give it a site's name or a
project/lang pair like :py:meth:`~earwigbot.wiki.SiteDB.get_site` takes, and
it'll remove that site from the sites database.

Sites
~~~~~

:py:class:`earwigbot.wiki.Site` objects provide the following attributes:

- :py:attr:`~earwigbot.wiki.Site.name`: the site's name (or "wikiid"), like
  ``"enwiki"``
- :py:attr:`~earwigbot.wiki.Site.project`: the site's project name, like
  ``"wikipedia"``
- :py:attr:`~earwigbot.wiki.Site.lang`: the site's language code, like ``"en"``
- :py:attr:`~earwigbot.wiki.Site.domain`: the site's web domain, like
  ``"en.wikipedia.org"``

and the following methods:

- :py:meth:`api_query(**kwargs) <earwigbot.wiki.Site.api_query>`: does an API
  query with the given keyword arguments as params
- :py:meth:`sql_query(query, params=(), ...) <earwigbot.wiki.Site.sql_query>`:
  does an SQL query and yields its results (as a generator)
- :py:meth:`~earwigbot.wiki.Site.get_replag`: returns the estimated database
  replication lag (if we have the site's SQL connection info)
- :py:meth:`namespace_id_to_name(id, all=False)
  <earwigbot.wiki.Site.namespace_id_to_name>`: given a namespace ID, returns
  the primary associated namespace name (or a list of all names when ``all`` is
  ``True``)
- :py:meth:`namespace_name_to_id(name)
  <earwigbot.wiki.Site.namespace_name_to_id>`: given a namespace name, returns
  the associated namespace ID
- :py:meth:`get_page(title, follow_redirects=False)
  <earwigbot.wiki.Site.get_page>`: returns a ``Page`` object for the given
  title (or a :py:class:`~earwigbot.wiki.Category` object if the page's
  namespace is "``Category:``")
- :py:meth:`get_category(catname, follow_redirects=False)
  <earwigbot.wiki.Site.get_category>`: returns a ``Category`` object for the
  given title (sans namespace)
- :py:meth:`get_user(username) <earwigbot.wiki.Site.get_user>`: returns a
  :py:class:`~earwigbot.wiki.User` object for the given username

Pages and categories
~~~~~~~~~~~~~~~~~~~~

Create :py:class:`earwigbot.wiki.Page` objects with
:py:meth:`site.get_page(title) <earwigbot.wiki.Site.get_page>`,
:py:meth:`page.toggle_talk() <earwigbot.wiki.Page.toggle_talk>`,
:py:meth:`user.get_userpage() <earwigbot.wiki.User.get_userpage>`, or
:py:meth:`user.get_talkpage() <earwigbot.wiki.User.get_talkpage>`. They provide
the following attributes:

- :py:attr:`~earwigbot.wiki.Page.title`: the page's title, or pagename
- :py:attr:`~earwigbot.wiki.Page.exists`: whether the page exists
- :py:attr:`~earwigbot.wiki.Page.pageid`: an integer ID representing the page
- :py:attr:`~earwigbot.wiki.Page.url`: the page's URL
- :py:attr:`~earwigbot.wiki.Page.namespace`: the page's namespace as an integer
- :py:attr:`~earwigbot.wiki.Page.protection`: the page's current protection
  status
- :py:attr:`~earwigbot.wiki.Page.is_talkpage`: ``True`` if the page is a
  talkpage, else ``False``
- :py:attr:`~earwigbot.wiki.Page.is_redirect`: ``True`` if the page is a
  redirect, else ``False``

and the following methods:

- :py:meth:`~earwigbot.wiki.Page.reload`: forcibly reload the page's attributes
  (emphasis on *reload* - this is only necessary if there is reason to believe
  they have changed)
- :py:meth:`toggle_talk(...) <earwigbot.wiki.Page.toggle_talk>`: returns a
  content page's talk page, or vice versa
- :py:meth:`~earwigbot.wiki.Page.get`: returns page content
- :py:meth:`~earwigbot.wiki.Page.get_redirect_target`: if the page is a
  redirect, returns its destination
- :py:meth:`~earwigbot.wiki.Page.get_creator`: returns a
  :py:class:`~earwigbot.wiki.User` object representing the first user to edit
  the page
- :py:meth:`edit(text, summary, minor=False, bot=True, force=False)
  <earwigbot.wiki.Page.edit>`: replaces the page's content with ``text`` or
  creates a new page
- :py:meth:`add_section(text, title, minor=False, bot=True, force=False)
  <earwigbot.wiki.Page.add_section>`: adds a new section named ``title`` at the
  bottom of the page
- :py:meth:`copyvio_check(...)
  <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_check>`: checks the page for
  copyright violations
- :py:meth:`copyvio_compare(url, ...)
  <earwigbot.wiki.copyvios.CopyvioMixin.copyvio_compare>`: checks the page like
  :py:meth:`~earwigbot.wiki.copyvios.CopyvioMixin.copyvio_check`, but
  against a specific URL

Additionally, :py:class:`~earwigbot.wiki.Category` objects (created with
:py:meth:`site.get_category(name) <earwigbot.wiki.Site.get_category>` or
:py:meth:`site.get_page(title) <earwigbot.wiki.Site.get_page>` where ``title``
is in the ``Category:`` namespace) provide the following additional method:

- :py:meth:`get_members(use_sql=False, limit=None)
  <earwigbot.wiki.Category.get_members>`: returns a list of page titles in the
  category (limit is ``50`` by default if using the API)

Users
~~~~~

Create :py:class:`earwigbot.wiki.User` objects with
:py:meth:`site.get_user(name) <earwigbot.wiki.Site.get_user>` or
:py:meth:`page.get_creator() <earwigbot.wiki.Page.get_creator>`. They provide
the following attributes:

- :py:attr:`~earwigbot.wiki.User.name`: the user's username
- :py:attr:`~earwigbot.wiki.User.exists`: ``True`` if the user exists, or
  ``False`` if they do not
- :py:attr:`~earwigbot.wiki.User.userid`: an integer ID representing the user
- :py:attr:`~earwigbot.wiki.User.blockinfo`: information about any current
  blocks on the user (``False`` if no block, or a dict of
  ``{"by": blocking_user, "reason": block_reason,
  "expiry": block_expire_time}``)
- :py:attr:`~earwigbot.wiki.User.groups`: a list of the user's groups
- :py:attr:`~earwigbot.wiki.User.rights`: a list of the user's rights
- :py:attr:`~earwigbot.wiki.User.editcount`: the number of edits made by the
  user
- :py:attr:`~earwigbot.wiki.User.registration`: the time the user registered as
  a :py:obj:`time.struct_time`
- :py:attr:`~earwigbot.wiki.User.emailable`: ``True`` if you can email the
  user, ``False`` if you cannot
- :py:attr:`~earwigbot.wiki.User.gender`: the user's gender (``"male"``,
  ``"female"``, or ``"unknown"``)

and the following methods:

- :py:meth:`~earwigbot.wiki.User.reload`: forcibly reload the user's attributes
  (emphasis on *reload* - this is only necessary if there is reason to believe
  they have changed)
- :py:meth:`~earwigbot.wiki.User.get_userpage`: returns a
  :py:class:`~earwigbot.wiki.Page` object representing the user's userpage
- :py:meth:`~earwigbot.wiki.User.get_talkpage`: returns a
  :py:class:`~earwigbot.wiki.Page` object representing the user's talkpage

Additional features
~~~~~~~~~~~~~~~~~~~

Not all aspects of the toolset are covered here. Explore `its code and
docstrings`_ to learn how to use it in a more hands-on fashion. For reference,
:py:attr:`bot.wiki <earwigbot.bot.Bot.wiki>` is an instance of
:py:class:`earwigbot.wiki.SitesDB` tied to the :file:`sites.db` file in the
bot's working directory.

.. _Pywikipedia framework:   http://pywikipediabot.sourceforge.net/
.. _its code and docstrings: https://github.com/earwig/earwigbot/tree/develop/earwigbot/wiki
