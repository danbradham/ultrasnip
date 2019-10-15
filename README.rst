
.. image:: https://raw.github.com/danbradham/ultrasnip/master/ultrasnip_sm.png
    :target: https://github.com/danbradham/ultrasnip
    :alt: UltraSnip

.. image:: https://img.shields.io/github/license/danbradham/ultrasnip.svg?style=flat-square
    :target: https://github.com/danbradham/ultrasnip/blob/master/LICENSE
    :alt: License


.. image:: https://raw.github.com/danbradham/ultrasnip/master/ultrasnip_sm.png
    :target: https://github.com/danbradham/ultrasnip
    :alt: UltraSnip

=========
UltraSnip
=========
A desktop snipping tool written in Qt for Python.

Unlike other desktop snipping tools - UltraSnip is written to help you make pixel-perfect captures.

.. image:: https://raw.github.com/danbradham/ultrasnip/master/ultrasnip_preview.png

Features
========

- Click + Drag region selection
- Corner and Side manipulator handles for adjusting region
- Corner Zoom previews to help achieve pixel perfect screen captures
- Use arrow keys to adjust manipulators in pixel increments

  - hold shift to move in 10 pixel increments
  - hold ctrl to move in 50 pixel increments

- Capture a region directly to a QPixmap


CLI Usage
=========

Measure a selected region.

.. code-block::

    > ultrasnip --measure
    > ultrasnip -m

Save the selected region to a file.

.. code-block::

    > ultrasnip --save output.png

Confirm the region after selection.

.. code-block::

    > ultrasnip --confirm


Ultra snip also supports pipes.

.. code-block::

    > ultrasnip > output.png


API Usage
=========

Select and capture a desktop region.

.. code-block::

    >>> import ultrasnip
    >>> pixmap = ultrasnip.select_and_capture()


Manually select a desktop region then capture it.

.. code-block::

    >>> region = ultrasnip.select()
    >>> pixmap = ultrasnip.capture_region(region)


Save a pixmap.

.. code-block::

    >>> pixmap.save('output.png')


Future Development
==================

- Add support for constaining aspect ratio
- Add support for specified resolution options
