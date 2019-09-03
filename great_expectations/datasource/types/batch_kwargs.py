import logging
import copy
from hashlib import md5
import datetime

import pandas as pd
from six import string_types
from great_expectations.types import RequiredKeysDotDict, AllowedKeysDotDict, ClassConfig
from great_expectations.datasource.types.reader_methods import ReaderMethods
# from great_expectations.exceptions import GreatExpectationsError

try:
    import pyspark
except ImportError:
    pyspark = None

logger = logging.getLogger(__name__)


class BatchFingerprint(AllowedKeysDotDict):
    _allowed_keys = AllowedKeysDotDict._allowed_keys | {
        "partition_id",
        "fingerprint"
    }
    _required_keys = AllowedKeysDotDict._required_keys | {
        "partition_id",
        "fingerprint"
    }
    _key_types = copy.copy(AllowedKeysDotDict._key_types).update({
        "partition_id": string_types,
        "fingerprint": string_types
    })

# class BatchFingerprint(object):
#     def __init__(self, partition_id, fingerprint, separator="__"):
#         self.__partition_id = partition_id
#         self.__fingerprint = fingerprint
#         self.__separator = separator
#
#     def __str__(self):
#         return self.__partition_id + self.separator + self.__fingerprint
#
#     # Act like a string when trying to concatenate
#     def __add__(self, other):
#         return str(self) + other
#
#     def __radd__(self, other):
#         return other + str(self)
#
#     # Return properties even though they are name mangled.
#     @property
#     def partition_id(self):
#         return self.__partition_id
#
#     @property
#     def fingerprint(self):
#         return self.__fingerprint
#
#     @property
#     def separator(self):
#         return self.__separator
#
#     @separator.setter
#     def separator(self, separator):
#         if separator not in ["::", ":", "_", "__"]:
#             raise GreatExpectationsError("Invalid separator: %s")
#         self.separator = separator


class BatchKwargs(RequiredKeysDotDict):
    """BatchKwargs represent uniquely identifying information for a Batch of data.

    BatchKwargs are generated by BatchGenerators and are interpreted by datasources.

    Note that by default, the partition_id *will* be included both in the partition_id portion and in the batch_kwargs
    hash portion of the batch_id.

    """
    _required_keys = set()
    # FIXME: Need discussion about whether we want to explicitly ignore, explicitly include, or just use whatever
    # is present

    _partition_id_key = "partition_id"

    # _batch_id_ignored_keys makes it possible to define keys which, if present, are ignored for purposes
    # of determining the unique batch id, such that batches differing only in the value in these keys are given
    # the same id
    _batch_id_ignored_keys = {
        "data_asset_type"
    }
    _key_types = {
        "data_asset_type": ClassConfig
    }

    @property
    def batch_fingerprint(self):
        partition_id = self.get(self._partition_id_key, None)
        # We do not allow a "None" partition_id, even if it's explicitly present as such in batch_kwargs
        if partition_id is None:
            partition_id = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%S.%fZ")
        id_keys = (set(self.keys()) - set(self._batch_id_ignored_keys)) - {self._partition_id_key}
        if len(id_keys) == 1:
            key = list(id_keys)[0]
            hash_ = key + ":" + self[key]
        else:
            hash_dict = {k: self[k] for k in id_keys}
            hash_ = md5(str(sorted(hash_dict.items())).encode("utf-8")).hexdigest()

        return BatchFingerprint(partition_id=partition_id, fingerprint=hash_)

    @classmethod
    def build_batch_fingerprint(cls, dict_):
        try:
            return BatchKwargs(dict_).batch_fingerprint
        except (KeyError, TypeError):
            logger.error("Unable to build BatchKwargs from provided dictionary.")
            return None


class PandasDatasourceBatchKwargs(BatchKwargs):
    """This is an abstract class and should not be instantiated. It's relevant for testing whether
    a subclass is allowed
    """
    pass


class SparkDFDatasourceBatchKwargs(BatchKwargs):
    """This is an abstract class and should not be instantiated. It's relevant for testing whether
    a subclass is allowed
    """
    pass


class SqlAlchemyDatasourceBatchKwargs(BatchKwargs):
    """This is an abstract class and should not be instantiated. It's relevant for testing whether
    a subclass is allowed
    """
    pass


class PathBatchKwargs(PandasDatasourceBatchKwargs, SparkDFDatasourceBatchKwargs):
    """PathBatchKwargs represents kwargs suitable for reading a file from a given path."""
    _required_keys = {
        "path"
    }
    # NOTE: JPC - 20190821: Eventually, we will probably want to have some logic that decides to use, say,
    # an md5 hash of a file instead of a path to decide when it's the same, or to differentiate paths
    # from s3 from paths on a local filesystem
    _key_types = {
        "path": string_types,
        "reader_method": ReaderMethods
    }


class MemoryBatchKwargs(PandasDatasourceBatchKwargs, SparkDFDatasourceBatchKwargs):
    _required_keys = {
        "df"
    }


class PandasDatasourceMemoryBatchKwargs(MemoryBatchKwargs):
    _required_keys = {
        "df"
    }
    _key_types = {
        "df": pd.DataFrame
    }


class SparkDFDatasourceMemoryBatchKwargs(MemoryBatchKwargs):
    _required_keys = {
        "df"
    }
    try:
        _key_types = {
            "df": pyspark.sql.DataFrame
        }
    except AttributeError:
        _key_types = {
            "df": None  # If we were unable to import pyspark, these are invalid
        }


class SqlAlchemyDatasourceTableBatchKwargs(SqlAlchemyDatasourceBatchKwargs):
    _required_keys = {
        "table"
        "timestamp"
    }
    _key_types = {
        "table": string_types,
        "timestamp": float
    }


class SqlAlchemyDatasourceQueryBatchKwargs(SqlAlchemyDatasourceBatchKwargs):
    _required_keys = {
        "query"
        "timestamp"
    }
    _key_types = {
        "query": string_types,
        "timestamp": float
    }


class SparkDFDatasourceQueryBatchKwargs(SparkDFDatasourceBatchKwargs):
    _required_keys = {
        "query",
        "timestamp"
    }
    _key_types = {
        "query": string_types,
        "timestamp": float
    }
