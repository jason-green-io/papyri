# PyNBT

PyNBT is a tiny, liberally licenced (MIT) NBT library.
It supports reading and writing big endian or little endian NBT files.

## Using the Library
Using the library in your own programs is simple and is capable of reading, modifying, and saving NBT files.

### Writing

**NOTE**: Beginning with version 1.1.0, names are optional for TAG_*'s that are added to a TAG_Compound, as they will be given the same name as their key. If you do
specify a name, it will be used instead. This breaks compatibility with old code, as the position of the `name` and `value` parameter have now swapped.

```python
from pynbt import NBTFile, TAG_Long, TAG_List, TAG_String

value = {
    'long_test': TAG_Long(104005),
    'list_test': TAG_List(TAG_String, [
        'Timmy',
        'Billy',
        'Sally'
    ])
}

nbt = NBTFile(value=value)
with open('out.nbt', 'wb') as io:
  nbt.save(io)
```

### Reading

Reading is simple, and will accept any file-like object providing `read()`.
Simply pretty-printing the file created from the example under writing:

```python
from pynbt import NBTFile

with open('out.nbt', 'rb') as io:
  nbt = NBTFile(io)
  print(nbt.pretty())
```

This produces the output:

```
TAG_Compound(''): 2 entries
{
  TAG_Long('long_test'): 104005
  TAG_List('list_test'): 3 entries
  {
    TAG_String(None): 'Timmy'
    TAG_String(None): 'Billy'
    TAG_String(None): 'Sally'
  }
}
```

Every tag exposes a minimum of two fields, `.name` and `.value`. Every tag's value maps to a plain Python type, such as a `dict()` for `TAG_Compound` and a `list()` for `TAG_List`. Every tag
also provides complete `__repr__` methods for printing. This makes traversal very simple and familiar to existing Python developers.

```python
with open('out.nbt', 'rb') as io:
  nbt = NBTFile(io)
  # Iterate over every TAG in the root compound as you would any other dict
  for name, tag in nbt.items():
      print(name, tag)

  # Print every tag in a list
  for tag in nbt['list_test']:
      print(tag)
```

## Changelog

These changelogs are summaries only and not comprehensive. See
the commit history between tags for full changes.

### v1.4.0
- **Removed** pocket detection helpers and ``RegionFile``, leaving PyNBT to **only** handle NBT.
- Added a simple unicode test.

### v1.3.0

- Internal cleanups in ``nbt.py`` to ease some C work.
- ``NBTFile.__init__()`` and ``NBTFile.save()``'s arguments have changed.
  For most cases changing ``compressed=True`` to ``NBTFIle.Compression.GZIP``
  will suffice.
- ``NBTFile.__init__()`` and ``NBTFile.save()`` no longer accept paths,
  instead accepting only file-like objects implementing ``read()`` and
  ``write()``, respectively.
- ``name`` must now be provided at construction or before saving of an
  ``NBTFile()`` (defaults to ``None`` instead of '').

### v1.2.

- TAG_List's values no longer need to be ``TAG_*`` objects. They
  will be converted when the tag is saved. This allows much  easier lists of
  native types.

### v1.2.0

- Internal code cleanup. Breaks compatibility with pocket loading
  and saving (to be reimplemented as helpers).
- Slight speed improvements.
- TAG_List can now be treated as a plain python list (`.value` points to `self`)

### v1.1.0

- Breaks compatibility with older code, but allows much more
  convenient creation of `TAG_Compound`. `name` and `value` have in most cases
  swapped spots.
- `name` is now the last argument of every `TAG_*`, and
  optional for children of a `TAG_Compound`. Instead, they'll be given the key
  they're assigned to as a name.
- `TAG_Compound`s can now be treated like
  dictionaries for convienience. `.value` simply maps to itself.

### v1.0.1

- Small bugfixes. 
- Adds support for `TAG_Int_Array`.

### v1.0.0

- First release.
