import pytest

import json
from collections import OrderedDict

from great_expectations.profile.base import DatasetProfiler
from great_expectations.profile.basic_dataset_profiler import BasicDatasetProfiler
from great_expectations.profile.columns_exist import ColumnsExistProfiler
from great_expectations.dataset.pandas_dataset import PandasDataset
import great_expectations as ge
from .test_utils import assertDeepAlmostEqual

# Tests to write:
# test_cli_method_works  -> test_cli
# test context-based profile methods
# test class-based profile methods


# noinspection PyPep8Naming
def test_DataSetProfiler_methods():
    toy_dataset = PandasDataset({"x": [1, 2, 3]})

    assert DatasetProfiler.validate(1) == False
    assert DatasetProfiler.validate(toy_dataset)

    with pytest.raises(NotImplementedError) as e_info:
        DatasetProfiler.profile(toy_dataset)


# noinspection PyPep8Naming
def test_ColumnsExistProfiler():
    toy_dataset = PandasDataset({"x": [1, 2, 3]})

    expectations_config, evr_config = ColumnsExistProfiler.profile(toy_dataset)

    assert len(expectations_config["expectations"]) == 1
    assert expectations_config["expectations"][0]["expectation_type"] == "expect_column_to_exist"
    assert expectations_config["expectations"][0]["kwargs"]["column"] == "x"


# noinspection PyPep8Naming
def test_BasicDatasetProfiler():
    toy_dataset = PandasDataset({"x": [1, 2, 3]}, data_asset_name="toy_dataset")
    assert len(toy_dataset.get_expectation_suite(
        suppress_warnings=True)["expectations"]) == 0

    expectations_config, evr_config = BasicDatasetProfiler.profile(toy_dataset)

    # print(json.dumps(expectations_config, indent=2))

    assert len(toy_dataset.get_expectation_suite(
        suppress_warnings=True)["expectations"]) > 0

    assert expectations_config["data_asset_name"] == "toy_dataset"
    assert "BasicDatasetProfiler" in expectations_config["meta"]

    assert set(expectations_config["meta"]["BasicDatasetProfiler"].keys()) == {
        "created_by", "created_at"
    }

    added_expectations = set()
    for exp in expectations_config["expectations"]:
        added_expectations.add(exp["expectation_type"])
        assert "BasicDatasetProfiler" in exp["meta"]
        assert "confidence" in exp["meta"]["BasicDatasetProfiler"]

    expected_expectations = {
        'expect_table_row_count_to_be_between',
        'expect_table_columns_to_match_ordered_list',
        'expect_column_values_to_be_in_set',
        'expect_column_unique_value_count_to_be_between',
        'expect_column_proportion_of_unique_values_to_be_between',
        'expect_column_values_to_not_be_null',
        'expect_column_values_to_be_in_type_list',
        'expect_column_values_to_be_unique'}

    assert expected_expectations.issubset(added_expectations)


# noinspection PyPep8Naming
def test_BasicDatasetProfiler_with_context(empty_data_context, filesystem_csv_2):
    empty_data_context.add_datasource(
        "my_datasource", "pandas", base_directory=str(filesystem_csv_2))
    not_so_empty_data_context = empty_data_context

    batch = not_so_empty_data_context.get_batch("my_datasource/f1")
    expectations_config, validation_results = BasicDatasetProfiler.profile(
        batch)

    # print(batch.get_batch_kwargs())
    # print(json.dumps(expectations_config, indent=2))

    assert expectations_config["data_asset_name"] == "my_datasource/default/f1"
    assert expectations_config["expectation_suite_name"] == "default"
    assert "BasicDatasetProfiler" in expectations_config["meta"]
    assert set(expectations_config["meta"]["BasicDatasetProfiler"].keys()) == {
        "created_by", "created_at", "batch_kwargs"
    }

    for exp in expectations_config["expectations"]:
        assert "BasicDatasetProfiler" in exp["meta"]
        assert "confidence" in exp["meta"]["BasicDatasetProfiler"]

    assert validation_results["meta"]["data_asset_name"] == "my_datasource/default/f1"
    assert set(validation_results["meta"].keys()) == {
        "great_expectations.__version__", "data_asset_name", "expectation_suite_name", "run_id", "batch_kwargs"
    }


# noinspection PyPep8Naming
def test_context_profiler(empty_data_context, filesystem_csv_2):
    """This just validates that it's possible to profile using the datasource hook, and have
    validation results available in the DataContext"""
    empty_data_context.add_datasource(
        "my_datasource", "pandas", base_directory=str(filesystem_csv_2))
    not_so_empty_data_context = empty_data_context

    assert not_so_empty_data_context.list_expectation_suites() == {}
    not_so_empty_data_context.profile_datasource("my_datasource", profiler=BasicDatasetProfiler)

    assert "my_datasource" in not_so_empty_data_context.list_expectation_suites()

    profiled_expectations = not_so_empty_data_context.get_expectation_suite('f1', "BasicDatasetProfiler")

    print(json.dumps(profiled_expectations, indent=2))
    for exp in profiled_expectations["expectations"]:
        assert "BasicDatasetProfiler" in exp["meta"]
        assert "confidence" in exp["meta"]["BasicDatasetProfiler"]

    assert profiled_expectations["data_asset_name"] == "my_datasource/default/f1"
    assert profiled_expectations["expectation_suite_name"] == "BasicDatasetProfiler"
    assert "batch_kwargs" in profiled_expectations["meta"]["BasicDatasetProfiler"]

    assert len(profiled_expectations["expectations"]) > 0


# noinspection PyPep8Naming
def test_BasicDatasetProfiler_on_titanic():
    """
    A snapshot test for BasicDatasetProfiler.
    We are running the profiler on the Titanic dataset
    and comparing the EVRs to ones retrieved from a
    previously stored file.
    """
    df = ge.read_csv("./tests/test_sets/Titanic.csv")
    df.profile(BasicDatasetProfiler)
    evrs = df.validate(result_format="SUMMARY")  # ["results"]

    # with open('tests/test_sets/expected_evrs_BasicDatasetProfiler_on_titanic.json', 'w+') as file:
    #     file.write(json.dumps(evrs))
    #
    # with open('tests/render/fixtures/BasicDatasetProfiler_evrs.json', 'w+') as file:
    #     file.write(json.dumps(evrs))

    with open('tests/test_sets/expected_evrs_BasicDatasetProfiler_on_titanic.json', 'r') as file:
        expected_evrs = json.load(file, object_pairs_hook=OrderedDict)

    expected_evrs.pop("meta")
    evrs.pop("meta")
    assertDeepAlmostEqual(expected_evrs, evrs)
