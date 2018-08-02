"""This command is to update the information of the documents.
Some examples of the usage are given below

Examples
^^^^^^^^

- Update a document automatically and interactively
  (searching by ``doi`` number in *crossref*, or in other sources...)

    .. code::

        papis update --auto -i "author = dyson"

- Update your library from a bib(la)tex file where many entries are listed.
  papis will try to look for documents in your library that match these
  entries and will ask you entry per entry to update it (of course this is
  done if you use the ``-i`` flag for interactively doing it). In the example
  ``libraryfile.bib`` is a file containing many entries.

    .. code::

        papis update --from-bibtex libraryfile.bib -i

"""

import papis
import six.moves.urllib.error as error
import logging
import papis.utils
import papis.bibtex
import papis.downloaders.utils
import papis.document
import papis.database
import papis.isbn
import papis.api
import papis.cli
import click

def run(
    document,
    data=dict(),
    interactive=False,
    force=False,
    from_yaml=False,
    from_bibtex=False,
    from_url=False,
    from_doi=False
        ):
    logger = logging.getLogger('update:run')

    if from_yaml:
        import yaml
        data.update(yaml.load(open(from_yaml)))

    elif from_bibtex:
        try:
            bib_data = papis.bibtex.bibtex_to_dict(from_bibtex)
            data.update(bib_data[0])
        except Exception:
            pass

    elif from_url:
        try:
            url_data = papis.downloaders.utils.get(from_url)
            data.update(url_data["data"])
        except Exception:
            pass

    elif from_doi:
        logger.debug("Try using doi %s" % from_doi)
        data.update(papis.utils.doi_to_data(from_doi))

    # Keep the ref the same, otherwise issues can be caused when
    # writing LaTeX documents and all the ref's change
    data['ref'] = document['ref']
    document.update(data, force, interactive)
    document.save()
    papis.database.get().update(document)



@click.command()
@click.help_option('--help', '-h')
@papis.cli.query_option()

@click.option(
    "-i",
    "--interactive",
    help="Interactively update",
    default=False,
    is_flag=True
)

@click.option(
    "-f",
    "--force",
    help="Force update, overwrite conflicting information",
    default=False,
    is_flag=True
)

@click.option(
    "-d",
    "--document",
    help="Overwrite an existing document",
    default=None
)

@click.option(
    "--from-isbnplus",
    help="Update info from isbnplus.org",
    default=None
)

@click.option(
    "--from-yaml",
    help="Update info from yaml file",
    default=None
)

@click.option(
    "--from-bibtex",
    help="Update info from bibtex file",
    default=None
)

@click.option(
    "--from-url",
    help="Get document or information from url",
    default=None
)

@click.option(
    "--from-doi",
    help="Doi to try to get information from",
    default=None
)

@click.option(
    "--auto",
    help="Try to parse information from different sources",
    default=False,
    is_flag=True
)

@click.option(
    "--all",
    help="Update all entries in library",
    default=False,
    is_flag=True
)

def cli(
        query,
        interactive,
        force,
        document,
        from_isbnplus,
        from_yaml,
        from_bibtex,
        from_url,
        from_doi,
        auto,
        all
        ):
    """Update a document from a given library"""
    # TODO: Try to recycle some of this code with command add.
    documents = papis.database.get().query(query)
    data = dict()
    logger = logging.getLogger('cli:update')

    if from_bibtex:
        bib_data = papis.bibtex.bibtex_to_dict(from_bibtex)
        # Then it means that the user wants to update all the information
        # appearing in the bibtex file
        if len(bib_data) > 1:
            logger.warning(
                'Your bibtex file contains more than one entry,'
            )
            logger.warning(
                'It is supposed that you want to update all the'
                'documents appearing inside the bibtex file.'
            )
            for bib_element in bib_data:
                doc = papis.document.Document(data=bib_element)
                located_doc = papis.utils.locate_document(doc, documents)
                if located_doc is None:
                    logger.error(
                        "The following information could not be located"
                    )
                    logger.error('\n'+papis.document.dump(doc))
                else:
                    run(
                        located_doc,
                        data=bib_element,
                        force=force,
                        interactive=interactive
                    )
            return 0

    # For the coming parts we need to pick a document
    if not all:
        document = [papis.cli.pick(documents)]
        if not document:
            return 0
    else:
        document = documents

    for docs in document:
        if all:
            data = dict()
            from_url = None
            from_doi = None
            from_isbnplus = None
        if auto:
            if 'doi' in docs.keys() and not from_doi:
                from_doi = docs['doi']
            elif 'url' in docs.keys() and not from_url:
                from_url = docs['url']
            elif 'title' in docs.keys() and not from_isbnplus:
                from_isbnplus = docs['title']


        if from_isbnplus:
            try:
                doc = papis.cli.pick(
                    [
                        papis.docs.Document(data=d)
                        for d in papis.isbn.get_data(
                            query=from_isbnplus
                        )
                    ]
                )
                if doc:
                    data.update(doc.to_dict())
            except urllib.error.HTTPError:
                logger.error('urllib failed to download')

        run(
            docs,
            data=data,
            interactive=interactive,
            force=force,
            from_yaml=from_yaml,
            from_bibtex=from_bibtex,
            from_url=from_url,
            from_doi=from_doi
        )

