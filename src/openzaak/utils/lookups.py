from typing import Tuple

from django.db.models.lookups import Exact as _Exact

from django_loose_fk.lookups import get_normalized_value
from django_loose_fk.virtual_models import ProxyMixin
from zgw_consumers.models.lookups import decompose_value

from .fields import FkOrServiceUrlField


@FkOrServiceUrlField.register_lookup
class Exact(_Exact):
    """
    combine Exact lookups for FkOrUrlField and ServiceUrlField
    """

    def get_cols(self) -> tuple:
        """ return tuple of cols for local fk, remote base url and remote relative url"""
        target = self.lhs.target
        db_table = target.model._meta.db_table

        return (
            target._fk_field.get_col(db_table),
            target._url_field._base_field.get_col(db_table),
            target._url_field._relative_field.get_col(db_table),
        )

    def get_prep_lookup(self):
        if not self.rhs_is_direct_value():
            return super().get_prep_lookup()

        if isinstance(self.rhs, ProxyMixin):
            self.rhs = self.rhs._loose_fk_data["url"]

        if isinstance(self.rhs, str):
            # dealing with a remote composite URL - return list
            fk_lhs, base_url_lhs, relative_url_lhs = self.get_cols()

            base_value, relative_value = decompose_value(self.rhs)
            base_normalized_value = get_normalized_value(base_value)[0]
            relative__normalized_value = get_normalized_value(relative_value)[0]
            return [
                base_url_lhs.field.get_prep_value(base_normalized_value),
                relative_url_lhs.field.get_prep_value(relative__normalized_value),
            ]

        # local URl
        return get_normalized_value(self.rhs)[0]

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

        if isinstance(self.rhs, str):
            # dealing with a remote composite URL
            sql = f"{base_lhs_sql} {rhs_sql} AND {relative_lhs_sql} {rhs_sql}"
        else:
            # dealing with a local URL
            sql = f"{fk_lhs_sql} {rhs_sql}"

        return sql, params
