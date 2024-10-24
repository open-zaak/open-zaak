# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2022 Dimpact
from typing import Tuple

from django.core.exceptions import EmptyResultSet
from django.db.models.lookups import Exact as _Exact, In as _In

from django_loose_fk.lookups import get_normalized_value
from django_loose_fk.virtual_models import ProxyMixin
from zgw_consumers.models.lookups import decompose_value

from .fields import FkOrServiceUrlField


class FkOrServiceUrlFieldMixin:
    def get_cols(self) -> tuple:
        """return tuple of cols for local fk, remote base url and remote relative url"""
        target = self.lhs.target
        db_table = target.model._meta.db_table

        return (
            target._fk_field.get_col(db_table),
            target._url_field._base_field.get_col(db_table),
            target._url_field._relative_field.get_col(db_table),
        )

    def split_lhs(
        self, compiler, connection
    ) -> Tuple[str, tuple, str, tuple, str, tuple]:

        fk_lhs, base_url_lhs, relative_url_lhs = self.get_cols()

        fk_lhs_sql, fk_params = self.process_lhs(compiler, connection, lhs=fk_lhs)
        base_lhs_sql, base_lhs_params = self.process_lhs(
            compiler, connection, lhs=base_url_lhs
        )
        relative_lhs_sql, relative_lhs_params = self.process_lhs(
            compiler, connection, lhs=relative_url_lhs
        )

        return (
            fk_lhs_sql,
            fk_params,
            base_lhs_sql,
            base_lhs_params,
            relative_lhs_sql,
            relative_lhs_params,
        )

    def get_prep_lookup(self) -> list:
        if not self.rhs_is_direct_value():
            return super().get_prep_lookup()

        fk_lhs, base_url_lhs, relative_url_lhs = self.get_cols()
        rhs_values = (
            self.rhs if self.get_db_prep_lookup_value_is_iterable else [self.rhs]
        )

        prepared_values = []
        for rhs_value in rhs_values:
            if isinstance(rhs_value, ProxyMixin):
                rhs_value = rhs_value._loose_fk_data["url"]

            if isinstance(rhs_value, str):
                # dealing with a remote composite URL - return list
                base_value, relative_value = decompose_value(rhs_value)
                base_normalized_value = get_normalized_value(base_value)[0]
                relative__normalized_value = get_normalized_value(relative_value)[0]
                prepared_value = [
                    base_url_lhs.field.get_prep_value(base_normalized_value),
                    relative_url_lhs.field.get_prep_value(relative__normalized_value),
                ]

            else:
                # local urls = return their pk
                prepared_value = get_normalized_value(rhs_value)[0]

            prepared_values.append(prepared_value)

        return (
            prepared_values[0]
            if not self.get_db_prep_lookup_value_is_iterable
            else prepared_values
        )


@FkOrServiceUrlField.register_lookup
class Exact(FkOrServiceUrlFieldMixin, _Exact):
    """
    combine Exact lookups for FkOrUrlField and ServiceUrlField
    """

    def get_db_prep_lookup(self, value, connection):
        # composite field
        if isinstance(value, list) and len(value) == 2:
            target = self.lhs.target

            sql = "%s"
            params = [
                target._url_field._base_field.get_db_prep_value(
                    value[0], connection, prepared=True
                ),
                target._url_field._relative_field.get_db_prep_value(
                    value[1], connection, prepared=True
                ),
            ]

            return sql, params

        return super().get_db_prep_lookup(value, connection)

    def as_sql(self, compiler, connection):
        # process lhs
        (
            fk_lhs_sql,
            fk_params,
            base_lhs_sql,
            base_lhs_params,
            relative_lhs_sql,
            relative_lhs_params,
        ) = self.split_lhs(compiler, connection)

        # process rhs
        rhs_sql, rhs_params = self.process_rhs(compiler, connection)
        rhs_sql = self.get_rhs_op(connection, rhs_sql)

        # combine
        params = rhs_params

        if isinstance(self.rhs, str) or (
            isinstance(self.rhs, list) and len(self.rhs) == 2
        ):
            # dealing with a remote composite URL
            sql = f"{base_lhs_sql} {rhs_sql} AND {relative_lhs_sql} {rhs_sql}"
        else:
            # dealing with a local URL
            sql = f"{fk_lhs_sql} {rhs_sql}"

        return sql, params


@FkOrServiceUrlField.register_lookup
class In(FkOrServiceUrlFieldMixin, _In):
    """
    Split the IN query into two IN queries, per datatype.

    Creates an IN query for the url field values, and an IN query for the FK
    field values, joined together by an OR.
    This realization will add additional DB query for every external url item in rhs list
    """

    lookup_name = "in"
    _connective = "OR"  # the connective used to connect the URL field query and the FK field query

    def process_rhs(self, compiler, connection):
        """
        separate list of values into two lists because we will use different expressions for them
        """
        if self.rhs_is_direct_value():
            target = self.lhs.target
            db_table = target.model._meta.db_table

            remote_rhs = [obj for obj in self.rhs if isinstance(obj, list)]
            local_rhs = [obj for obj in self.rhs if obj not in remote_rhs]

            if remote_rhs:
                url_lhs = target._url_field.get_col(db_table)

                _remote_lookup = _In(url_lhs, remote_rhs)
                url_rhs_sql, url_rhs_params = _remote_lookup.process_rhs(
                    compiler, connection
                )
            else:
                url_rhs_sql, url_rhs_params = None, ()

            # filter out the remote objects
            if local_rhs:
                fk_lhs = target._fk_field.get_col(db_table)

                _local_lookup = _In(fk_lhs, local_rhs)
                fk_rhs_sql, fk_rhs_params = _local_lookup.process_rhs(
                    compiler, connection
                )
            else:
                fk_rhs_sql, fk_rhs_params = None, ()

        else:
            # we're dealing with something that can be expressed as SQL -> it's local only!
            url_rhs_sql, url_rhs_params = None, ()
            fk_rhs_sql, fk_rhs_params = super().process_rhs(compiler, connection)

        return url_rhs_sql, url_rhs_params, fk_rhs_sql, fk_rhs_params

    def build_fk_sql_if_url_sql_empty(self, fk_sql, fk_params, fk_lhs_sql):
        return fk_sql, fk_params

    def build_url_sql_if_fk_sql_empty(
        self, url_sql, url_params, base_lhs_sql, relative_lhs_sql
    ):
        return url_sql, url_params

    def as_sql(self, compiler, connection):
        # process lhs
        (
            fk_lhs_sql,
            fk_lhs_params,
            base_lhs_sql,
            base_lhs_params,
            relative_lhs_sql,
            relative_lhs_params,
        ) = self.split_lhs(compiler, connection)

        # process rhs
        url_rhs_sql, url_rhs_params, fk_rhs_sql, fk_params = self.process_rhs(
            compiler, connection
        )

        # combine
        if not fk_rhs_sql and not url_rhs_sql:
            raise EmptyResultSet()

        if fk_rhs_sql:
            fk_rhs_sql = self.get_rhs_op(connection, fk_rhs_sql)
            fk_sql = "{} {}".format(fk_lhs_sql, fk_rhs_sql)
        else:
            fk_sql = None

        if url_rhs_sql:
            url_rhs_sql = "IN (" + ", ".join(["(%s, %s)"] * len(url_rhs_params)) + ")"
            url_sql = f"({base_lhs_sql}, {relative_lhs_sql}) {url_rhs_sql}"
            # flatten param list
            url_params = sum(url_rhs_params, [])
        else:
            url_sql = None
            url_params = []

        if not fk_sql:
            return self.build_url_sql_if_fk_sql_empty(
                url_sql, url_params, base_lhs_sql, relative_lhs_sql
            )

        if not url_sql:
            return self.build_fk_sql_if_url_sql_empty(fk_sql, fk_params, fk_lhs_sql)

        params = url_params + list(fk_params)
        sql = "({} {} {})".format(url_sql, self._connective, fk_sql)

        return sql, params


@FkOrServiceUrlField.register_lookup
class NotIn(In):
    lookup_name = "not_in"
    # using an AND here, because negation of the entire __in operation means that OR turns
    # into AND
    _connective = "AND"

    def build_fk_sql_if_url_sql_empty(self, fk_sql, fk_params, fk_lhs_sql):
        """
        If no filter on URLs is there, make sure that rows with empty FK fields
        show up as well
        """
        fk_sql = f"{fk_sql} OR {fk_lhs_sql} IS NULL"
        return fk_sql, fk_params

    def build_url_sql_if_fk_sql_empty(
        self, url_sql, url_params, base_lhs_sql, relative_lhs_sql
    ):
        """
        If no filter on FKs is there, make sure that rows with empty URL fields
        show up as well
        """
        url_sql = f"{url_sql} OR {base_lhs_sql} IS NULL AND {relative_lhs_sql} IS NULL"
        return url_sql, url_params

    def as_sql(self, compiler, connection):
        sql, params = super().as_sql(compiler, connection)
        sql = "NOT {}".format(sql)
        return sql, params
