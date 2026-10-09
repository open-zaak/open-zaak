.. _installation_reference_overwritten_documents:

Detecting overwritten documents
===============================

Until the fix for :open-zaak:`2592`, three bugs could silently replace the content of a
document with the content of another document. The
``detect_overwritten_documents`` command lists documents that may have been affected.
This page explains what it checks, the reasoning behind each check and when that
reasoning fails, so you can judge the results yourself.

In short
--------

Run the command in an Open Zaak container, and keep its output:

.. code-block:: bash

    python src/manage.py detect_overwritten_documents > report.tsv

It ends with a summary like this (on stderr):

.. code-block:: text

    Affected: 2 (1 shared-file, 1 wrong-size) - almost certainly lost their content
    Possible: 14 (12 same-name, 2 missing-file) - can't be ruled out, inspect these
    Unlikely: 4021 (4019 same-name, 2 size-unknown) - ruled out by the timing model, or rare causes only

* **Affected**: these documents almost certainly lost their content. Ask the
  application that created them to upload them again.
* **Possible**: the command can't rule these out. Inspect them: compare each with the
  original in the application that uploaded it.
* **Unlikely**: the command ruled these out, under the assumptions explained below.
  Most installations can leave them. If you want a number on the remaining risk,
  inspect a random sample (see `Estimating the remaining risk`_).

``tail -n +2 report.tsv | sort`` lists the findings in this order, without the header.

A document that isn't listed at all is fine, except for the cases in
`What can't be detected`_.

The bugs
--------

Which bugs apply depends on the storage backend, ``DOCUMENTEN_API_BACKEND``. If you
switched backends, consider every backend you used since 1.8.0.

==========================  =====================  ==============  =================
``DOCUMENTEN_API_BACKEND``  1. Large file uploads  2. Bulk import  3. Same-name save
==========================  =====================  ==============  =================
``filesystem`` (default)    affected               affected        not affected
``azure_blob_storage``      affected               not affected    not affected
``s3_storage``              affected               not affected    affected
==========================  =====================  ==============  =================

1. **Large file uploads** (1.8.0 and later). An application creates a document with a
   ``bestandsomvang`` but without ``inhoud``, uploads the ``bestandsdelen`` and
   unlocks the document. The unlock merged the parts into a temporary file on local
   disk, ``PRIVATE_MEDIA_ROOT/<name>``, with the name derived from the
   ``bestandsnaam``, and then stored that file. Two unlocks of documents with the same
   name at the same time used the same temporary file:

   * Both write their parts into it at their own position, so the result can be the
     other document's content, a truncated copy or a mix of both. A mix can have
     exactly the right size, even when the other document is smaller.
   * One unlock can delete the file while the other still needs it. That unlock fails
     with a server error and leaves the document unlocked without content; its parts
     are still there.

   This applies to every backend, because the temporary file was always on local disk.
2. **Bulk import** (1.13.0 and later, ``filesystem`` only). Importing a file whose
   name already existed in that month's upload directory (``uploads/YYYY/MM/``)
   replaced it: files of other rows in the same import, of earlier imports, and of
   documents created through the API. When a row failed later, its file was deleted,
   even if another document still used it.
3. **Same-name saves** (1.27.0 and later, ``s3_storage`` only). Two saves of documents
   with the same name at the same time could both pick the same object key; the last
   upload won. This applies to creating, updating, unlocking and importing documents.
   ``filesystem`` creates files exclusively and Azure refuses to overwrite a blob, so
   there concurrent saves got a unique name or an explicit error.

With ``S3_FILE_OVERWRITE=True``, documents with the same name always overwrite each
other, also after the fix: that's what the setting is for.

Installations that stored documents in a DMS through CMIS (1.8.0 up to 1.26.0) used
the same merge code for large file uploads. Those documents are in the DMS, so this
command can't check them.

What the command checks
-----------------------

For every version of every document with a file, the command compares the file in
storage with the metadata in the database. Versions of the same document normally
share a file; that's not a problem.

``affected``
^^^^^^^^^^^^

``shared-file``
    Documents (not versions of one document) point to the same file. At most one of
    them has its own content; usually the one saved last. Caused by 2 or 3, or by
    ``S3_FILE_OVERWRITE=True``.

    *Can be wrong when*: the documents had the same content anyway, e.g. because the
    same file was imported twice.
``wrong-size``
    The file's size differs from the document's ``bestandsomvang``. Caused by 1, 2 or 3.

    *Can be wrong when*: the ``bestandsomvang`` was wrong to begin with, e.g. in a bulk
    import file. Compare the background rates in the summary (see
    `Background rates`_).
``wrong-hash``
    The file doesn't match the document's ``integriteit`` (md5, sha_1, sha_256 or
    sha_512 only). Only checked with ``--verify-integrity``. Caused by 1, 2 or 3.

    *Can be wrong when*: the application sent a wrong hash, or a hash in another
    encoding than hexadecimal or base64.

``possible``
^^^^^^^^^^^^

``same-name``
    The document has the same name as another document, its size is right, there's no
    hash to prove its content is its own, and their unlocks may have overlapped in time
    (see `The timing model`_). The detail says how far apart they were, and why the
    content couldn't be verified.
``missing-file``
    The file doesn't exist. Caused by 2, by a deleted document that shared its file with
    this one (case 2 or 3: deleting a document deletes its file), or by files removed
    outside Open Zaak, e.g. a database restored without its files.
``no-content``
    The document is unlocked, has a ``bestandsomvang`` but no content, and all its
    ``bestandsdelen`` were uploaded: its unlock failed (case 1, or another error). The
    content isn't lost: it's still in the ``bestandsdelen``.
``not-checked``
    The file couldn't be checked, e.g. because the storage wasn't reachable or denied
    access. The detail has the error. Run the command again.

``unlikely``
^^^^^^^^^^^^

``same-name``
    As above, but the timing model rules out that the unlocks overlapped.
``size-unknown``
    The document has no ``bestandsomvang`` and no hash, so its content can't be checked
    at all, and no document with the same name exists. Only rare failures could have
    overwritten it: an import batch that was rolled back after its files were copied,
    a crashed worker, or an S3 save that failed after its upload. Common for imported
    documents, because ``bestandsomvang`` is optional in the import file.

The timing model
----------------

Two documents with the same name could only get each other's content if their unlocks
merged at the same time. The command estimates whether that was possible.

**What we know.** ``begin_registratie`` of a document version is set every time that
version is saved. An unlock saves the version right after it stored the merged file,
so for a version that got its content by an unlock, ``begin_registratie`` is the end of
that unlock.

**What we assume.** An unlock took at most

.. code-block:: text

    bestandsomvang / minimum throughput + margin

* The *minimum throughput* is the slowest plausible speed of merging the parts and
  storing the result, together. Default: 256 KiB/s, ``--min-throughput``. Local disks
  and object storage in the same data centre are usually much faster.
* The *margin* covers request overhead and clock differences between the servers
  running Open Zaak. Default: 30 seconds, ``--margin``.

**The window.** Two unlocks can only have overlapped if their ``begin_registratie``
differ by less than the window of the larger document. For example, two 19 MiB
documents: 19 MiB / 256 KiB/s + 30 s ≈ 106 s. If they were saved a day apart, they
can't have overlapped.

**When the model can't tell**, and the document stays ``possible``:

* The document, or a document with the same name, was edited in the admin. That saves
  the version again, moving ``begin_registratie``. The command finds these in the admin
  history.
* A document with the same name has no ``bestandsomvang``.
* A document with the same name failed to unlock (no content, but ``bestandsdelen``).
  Its unlock happened at an unknown time after its last save, so only documents that
  were unlocked before that are ruled out.

**When the model is wrong**, and a document is ``unlikely`` while it isn't:

* Your unlocks were slower than the assumed throughput, e.g. because of a slow or busy
  network to the object storage. Run again with a lower ``--min-throughput``.
* Your servers' clocks differed by more than the margin. Run again with a larger
  ``--margin``.
* A version was saved again after its unlock in another way than through the admin:
  a script, a database migration or a direct change in the database.
* The document that overwrote this one has been deleted since (see
  `What can't be detected`_).

The ``--format jsonl`` output has the numbers for every ``same-name`` finding: the
``begin_registratie`` and ``bestandsomvang`` of the document and of its namesakes, the
time between them and the window. You can apply your own assumptions to those.

Background rates
----------------

Documents without a namesake can't have been affected by concurrent unlocks, so their
rates of ``wrong-size`` and ``missing-file`` show what's normal for your installation,
e.g. because of wrong ``bestandsomvang`` values in old imports. The summary shows both,
with 95% intervals:

.. code-block:: text

    Background rates, with 95% intervals:
      wrong-size: 3/2104 (0.05%-0.42%) with a namesake, 41/96210 (0.03%-0.06%) without a namesake

If the rate with a namesake isn't clearly higher than without, the ``wrong-size``
findings among documents with a namesake are probably not caused by the unlocks.

Estimating the remaining risk
-----------------------------

The command can't verify ``unlikely`` documents itself. If you want to know how many of
them could be affected, inspect a random sample:

.. code-block:: bash

    grep ^unlikely report.tsv | shuf -n 100 --random-source=report.tsv > sample.tsv

If none of the *n* inspected documents turns out to be affected, at most about
*3 / n* of all ``unlikely`` documents are, with 95% confidence (the "rule of three"):
0 of 100 means at most 3%. If you find affected documents, inspect all of them, or ask
the applications to upload every ``unlikely`` document again.

What can't be detected
----------------------

* A document that got another document's content of exactly the same size, without a
  hash, when that other document has been deleted since. Deleting a document also
  deletes its audit trail, so there's nothing left to compare it with.
* A document overwritten by a document that never reached the database (a rolled back
  import batch, a crashed worker, a failed S3 save), when the overwriting file had the
  same size and there's no hash.
* Two unlocks of the *same* document at the same time, e.g. by a retry, when the result
  has the right size and there's no hash.
* Documents stored in a DMS through CMIS.

Running it
----------

The command only reads; it can run on a live installation. It prints its findings to
stdout and the summary to stderr.

* On ``filesystem`` storage it's quick: it checks the files on local disk.
* On Azure and S3 it makes one metadata request per file (``HEAD``, without downloading
  content), which can take hours for millions of documents. ``--quick`` only checks
  documents with a namesake, as a first pass; it skips ``wrong-size`` and
  ``missing-file`` for all other documents.
* ``--verify-integrity`` reads every file with a hash completely. Blobs in Azure's
  archive tier can't be read; they're reported as ``not-checked``.

For a long run, start it where it won't be interrupted, e.g. as a Kubernetes Job with
the same image and environment as your Open Zaak deployment, and collect the output
with ``kubectl logs``. Findings are written as they are found, so an interrupted run
still leaves the findings so far; the output is complete when the summary has been
printed.

``--format jsonl`` prints one JSON object per finding, with all the evidence, for your
own analysis.

What to do with the findings
----------------------------

Open Zaak itself can't recover lost content:

* Ask the application that created the document to upload it again.
* For bulk imports: the import report lists the ``uuid`` and ``bestandspad`` of every
  document; the original files may still be in the import directory.
* On S3 with bucket versioning, the overwritten versions of a ``shared-file`` object
  can be restored.
* For ``no-content``: the content is still in the ``bestandsdelen``.
