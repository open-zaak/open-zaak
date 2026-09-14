# SPDX-License-Identifier: EUPL-1.2
# Copyright (C) 2019 - 2020 Dimpact

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from privates.test import temp_private_root

from ..factories import EnkelvoudigInformatieObjectFactory


@temp_private_root()
class EIOTests(TestCase):
    def test_file_name_may_be_larger_then_100_chars(self):
        """
        #2385 Test to ensure that files with long names can be created.
        It used to produce the following error:

        django.core.exceptions.SuspiciousFileOperation: Storage can not find an available filename for ...
        Please make sure that the corresponding file field allows sufficient "max_length".

        This is because the default max length of a file field within django is 100 chars.
        """

        file = SimpleUploadedFile(
            "name_which_is_a_lot_longer_then_one_"
            "hundred_characters_to_showcase_that_"
            "the_max_length_error_will_not_trigger_on_most_files",
            b"filecontentstring",
        )

        EnkelvoudigInformatieObjectFactory.create(inhoud=file)
