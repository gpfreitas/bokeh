from __future__ import absolute_import

from copy import copy
from itertools import cycle

from bokeh.charts import DEFAULT_PALETTE
from bokeh.charts.properties import ColumnLabel
from bokeh.charts.utils import marker_types
from bokeh.enums import DashPattern
from bokeh.models.sources import ColumnDataSource
from bokeh.properties import (HasProps, String, List, Instance, Either, Any, Dict,
                              Color, Bool)


class AttrSpec(HasProps):
    """A container for assigning attributes to values and retrieving them as needed.

    A special function this provides is automatically handling cases where the provided
    iterator is too short compared to the distinct values provided.

    Once created as attr_spec, you can do attr_spec[data_label], where data_label must
    be a one dimensional tuple of values, representing the unique group in the data.

    See the :meth:`AttrSpec.setup` method for the primary way to provide an existing
    AttrSpec with data and column values and update all derived property values.
    """

    id = Any()
    data = Instance(ColumnDataSource)
    name = String(help='Name of the attribute the spec provides.')

    columns = Either(ColumnLabel, List(ColumnLabel), help="""
        The label or list of column labels that correspond to the columns that will be
        used to find all distinct values (single column) or combination of values (
        multiple columns) to then assign a unique attribute to. If not enough unique
        attribute values are found, then the attribute values will be cycled.
        """)

    default = Any(default=None, help="""
        The default value for the attribute, which is used if no column is assigned to
        the attribute for plotting. If the default value is not provided, the first
        value in the `iterable` property is used.
        """)

    attr_map = Dict(Any, Any, help="""
        Created by the attribute specification when `iterable` and `data` are
        available. The `attr_map` will include a mapping between the distinct value(s)
        found in `columns` and the attribute value that has been assigned.
        """)

    iterable = List(Any, default=None, help="""
        The iterable of attribute values to assign to the distinct values found in
        `columns` of `data`.
        """)

    items = List(Any, default=None, help="""
        The attribute specification calculates this list of distinct values that are
        found in `columns` of `data`.
        """)

    sort = Bool(default=True, help="""
        A boolean flag to tell the attribute specification to sort `items`, when it is
        calculated. This affects which value of `iterable` is assigned to each distinct
        value in `items`.
        """)

    ascending = Bool(default=True, help="""
        A boolean flag to tell the attribute specification how to sort `items` if the
        `sort` property is set to `True`. The default setting for `ascending` is `True`.
        """)

    def __init__(self, columns=None, df=None, iterable=None, default=None,
                 items=None, **properties):
        """Create a lazy evaluated attribute specification.

        Args:
            columns: a list of column labels
            df(:class:`~pandas.DataFrame`): the data source for the attribute spec.
            iterable: an iterable of distinct attribute values
            default: a value to use as the default attribute when no columns are passed
            items: the distinct values in columns. If items is provided as input,
                then the values provided are used instead of being calculated. This can
                be used to force a specific order for assignment.
            **properties: other properties to pass to parent :class:`HasProps`
        """
        properties['columns'] = self._ensure_list(columns)

        if df is not None:
            properties['data'] = ColumnDataSource(df)

        if default is None and iterable is not None:
            default_iter = copy(iterable)
            properties['default'] = next(iter(default_iter))
        elif default is not None:
            properties['default'] = default

        if iterable is not None:
            properties['iterable'] = iterable

        if items is not None:
            properties['items'] = items

        super(AttrSpec, self).__init__(**properties)

    @staticmethod
    def _ensure_list(attr):
        """Always returns a list with the provided value. Returns the value if a list."""
        if isinstance(attr, str):
            return [attr]
        elif isinstance(attr, tuple):
            return list(attr)
        else:
            return attr

    @staticmethod
    def _ensure_tuple(attr):
        """Return tuple with the provided value. Returns the value if a tuple."""
        if not isinstance(attr, tuple):
            return (attr,)
        else:
            return attr

    def _setup_default(self):
        """Stores the first value of iterable into `default` property."""
        self.default = next(self._setup_iterable())

    def _setup_iterable(self):
        """Default behavior is to copy and cycle the provided iterable."""
        return cycle(copy(self.iterable))

    def _generate_items(self, df, columns):
        """Produce list of unique tuples that identify each item."""
        if self.items is None or len(self.items) == 0:
            if self.sort:
                df = df.sort(columns=columns, ascending=self.ascending)
            items = df[columns].drop_duplicates()
            self.items = [tuple(x) for x in items.to_records(index=False)]

    def _create_attr_map(self, df, columns):
        """Creates map between unique values and available attributes."""

        self._generate_items(df, columns)
        iterable = self._setup_iterable()

        iter_map = {}
        for item in self.items:
            item = self._ensure_tuple(item)
            iter_map[item] = next(iterable)
        return iter_map

    def set_columns(self, columns):
        """Set columns property and update derived properties as needed."""
        columns = self._ensure_list(columns)
        if all([col in self.data.column_names for col in columns]):
            self.columns = columns
        else:
            # we have input values other than columns
            # assume this is now the iterable at this point
            self.iterable = columns
            self._setup_default()

    def setup(self, data=None, columns=None):
        """Set the data and update derived properties as needed."""
        if data is not None:
            self.data = data

            if columns is not None:
                self.set_columns(columns)

        if self.columns is not None and self.data is not None:
            self.attr_map = self._create_attr_map(self.data.to_df(), self.columns)

    def __getitem__(self, item):
        """Lookup the attribute to use for the given unique group label."""

        if not self.columns or not self.data or item is None:
            return self.default
        elif self._ensure_tuple(item) not in self.attr_map.keys():

            # make sure we have attr map
            self.setup()

        return self.attr_map[self._ensure_tuple(item)]


class ColorAttr(AttrSpec):
    """An attribute specification for mapping unique data values to colors.

    .. note::
        Should be expanded to support more complex coloring options.
    """
    name = 'color'
    iterable = List(Color, default=DEFAULT_PALETTE)

    def __init__(self, **kwargs):
        iterable = kwargs.pop('palette', None)
        if iterable is not None:
            kwargs['iterable'] = iterable
        super(ColorAttr, self).__init__(**kwargs)


class MarkerAttr(AttrSpec):
    """An attribute specification for mapping unique data values to markers."""
    name = 'marker'
    iterable = List(String, default=list(marker_types.keys()))

    def __init__(self, **kwargs):
        iterable = kwargs.pop('markers', None)
        if iterable is not None:
            kwargs['iterable'] = iterable
        super(MarkerAttr, self).__init__(**kwargs)


dashes = DashPattern._values


class DashAttr(AttrSpec):
    """An attribute specification for mapping unique data values to line dashes."""
    name = 'dash'
    iterable = List(String, default=dashes)

    def __init__(self, **kwargs):
        iterable = kwargs.pop('dash', None)
        if iterable is not None:
            kwargs['iterable'] = iterable
        super(DashAttr, self).__init__(**kwargs)


class CatAttr(AttrSpec):
    """An attribute specification for mapping unique data values to labels.

    .. note::
        this is a special attribute specification, which is used for defining which
        labels are used for one aspect of a chart (grouping) vs another (stacking or
        legend)
    """
    name = 'nest'

    def __init__(self, **kwargs):
        super(CatAttr, self).__init__(**kwargs)

    def _setup_iterable(self):
        return iter(self.items)

    def get_levels(self, columns):
        """Provides a list of levels the attribute represents."""
        if self.columns is not None:
            levels = [columns.index(col) for col in self.columns]
            return levels
        else:
            return []


""" Attribute Spec Functions

Convenient functions for producing attribute specifications. These would be
the interface used by end users when providing attribute specs as inputs
to the Chart.
"""


def color(columns=None, palette=None, **kwargs):
    """Produces a ColorAttr specification for coloring groups of data based on columns.

    Args:
        columns (str or list(str), optional): a column or list of columns for coloring
        palette (list(str), optional): a list of colors to use for assigning to unique
            values in `columns`.
        **kwargs: any keyword, arg supported by :class:`AttrSpec`

    Returns:
        a `ColorAttr` object
    """
    if palette is not None:
        kwargs['palette'] = palette

    kwargs['columns'] = columns
    return ColorAttr(**kwargs)


def marker(columns=None, markers=None, **kwargs):

    """ Specifies detailed configuration for a marker attribute.

    Args:
        columns (list or str):
        markers (list(str) or str): a custom list of markers. Must exist within
            :data:`marker_types`.
        **kwargs: any keyword, arg supported by :class:`AttrSpec`

    Returns:
        a `MarkerAttr` object
    """
    if markers is not None:
        kwargs['markers'] = markers

    kwargs['columns'] = columns
    return MarkerAttr(**kwargs)


def cat(columns=None, cats=None, sort=True, ascending=True, **kwargs):
    """ Specifies detailed configuration for a chart attribute that uses categoricals.

    Args:
        columns (list or str): the columns used to generate the categorical variable
        cats (list, optional): overrides the values derived from columns
        sort (bool, optional): whether to sort the categorical values (default=True)
        ascending (bool, optional): whether to sort the categorical values (default=True)
        **kwargs: any keyword, arg supported by :class:`AttrSpec`

    Returns:
        a `CatAttr` object
    """
    if cats is not None:
        kwargs['cats'] = cats

    kwargs['columns'] = columns
    kwargs['sort'] = sort
    kwargs['ascending'] = ascending

    return CatAttr(**kwargs)
