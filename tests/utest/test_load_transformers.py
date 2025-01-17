from unittest.mock import Mock, patch

import pytest

from robotidy.skip import SkipConfig
from robotidy.transformers import load_transformers
from robotidy.utils import ROBOT_VERSION


@pytest.fixture(scope="session")
def skip_config():
    return SkipConfig()


class TestLoadTransformers:
    def test_transformer_order(self, skip_config):
        order_1 = ["NormalizeSeparators", "OrderSettings"]
        order_2 = ["OrderSettings", "NormalizeSeparators"]
        transformers_1 = load_transformers(
            [(transf, []) for transf in order_1], {}, skip=skip_config, target_version=ROBOT_VERSION.major
        )
        transformers_2 = load_transformers(
            [(transf, []) for transf in order_2], {}, skip=skip_config, target_version=ROBOT_VERSION.major
        )
        assert all(t1.name == t2.name for t1, t2 in zip(transformers_1, transformers_2))

    def test_transformer_force_order(self, skip_config):
        # default_order = ['NormalizeSeparators', 'OrderSettings']
        custom_order = ["OrderSettings", "NormalizeSeparators"]
        transformers = load_transformers(
            [(transf, []) for transf in custom_order],
            {},
            skip=skip_config,
            force_order=True,
            target_version=ROBOT_VERSION.major,
        )
        assert all(t1.name == t2 for t1, t2 in zip(transformers, custom_order))

    def test_disabled_transformer(self, skip_config):
        transformers = load_transformers(None, {}, skip=skip_config, target_version=ROBOT_VERSION.major)
        assert all(transformer.name != "SmartSortKeywords" for transformer in transformers)

    def test_enable_disable_transformer(self, skip_config):
        transformers = load_transformers(
            [("SmartSortKeywords", [])], {}, skip=skip_config, target_version=ROBOT_VERSION.major
        )
        assert transformers[0].name == "SmartSortKeywords"

    def test_configure_transformer(self, skip_config):
        transformers = load_transformers(
            None, {"AlignVariablesSection": ["up_to_column=4"]}, skip=skip_config, target_version=ROBOT_VERSION.major
        )
        transformers_not_configured = load_transformers(None, {}, skip=skip_config, target_version=ROBOT_VERSION.major)
        assert len(transformers) == len(transformers_not_configured)
        for transformer in transformers:
            if transformer.name == "AlignVariablesSection":
                assert transformer.instance.up_to_column + 1 == 4

    def test_configure_transformer_overwrite(self, skip_config):
        transformers = load_transformers(
            [("AlignVariablesSection", ["up_to_column=3"])],
            {"AlignVariablesSection": ["up_to_column=4"]},
            skip=skip_config,
            target_version=ROBOT_VERSION.major,
        )
        assert transformers[0].instance.up_to_column + 1 == 4

    @pytest.mark.parametrize("force_order", [True, False])
    @pytest.mark.parametrize("allow_disabled", [True, False])
    @pytest.mark.parametrize(
        "transformers, configure, present, test_for",
        [
            # robotidy .
            (None, {}, True, "AlignVariablesSection"),
            # robotidy -c AlignVariablesSection:enabled=True .
            (None, {"AlignVariablesSection": ["enabled=True"]}, True, "AlignVariablesSection"),
            # robotidy -c AlignVariablesSection:enabled=false .
            (None, {"AlignVariablesSection": ["enabled=false"]}, False, "AlignVariablesSection"),
            # robotidy -c SmartSortKeywords:enabled=True .
            (None, {"SmartSortKeywords": ["enabled=True"]}, True, "SmartSortKeywords"),  # disabled by default
            # robotidy -c SmartSortKeywords:enabled=False .
            (None, {"SmartSortKeywords": ["enabled=False"]}, False, "SmartSortKeywords"),
            # robotidy --transform SmartSortKeywords:enabled=True .
            ([("SmartSortKeywords", ["enabled=True"])], {}, True, "SmartSortKeywords"),
            # robotidy --transform NormalizeAssignments .
            ([("NormalizeAssignments", [])], {}, False, "AlignVariablesSection"),
            # robotidy --transform NormalizeAssignments --transform AlignVariablesSection .
            ([("NormalizeAssignments", []), ("AlignVariablesSection", [])], {}, True, "AlignVariablesSection"),
            # robotidy --transform NormalizeAssignments --transform AlignVariablesSection:up_to_column=4 .
            (
                [("NormalizeAssignments", []), ("AlignVariablesSection", ["up_to_column=4"])],
                {},
                True,
                "AlignVariablesSection",
            ),
            # robotidy --transform NormalizeAssignments --transform AlignVariablesSection:up_to_column=4:enabled=True .
            (
                [("NormalizeAssignments", []), ("AlignVariablesSection", ["up_to_column=4", "enabled=True"])],
                {},
                True,
                "AlignVariablesSection",
            ),
            # robotidy --transform NormalizeAssignments --transform AlignVariablesSection:up_to_column=4:enabled=False .
            (
                [("NormalizeAssignments", []), ("AlignVariablesSection", ["up_to_column=4", "enabled=False"])],
                {},
                False,
                "AlignVariablesSection",
            ),
            # robotidy --transform NormalizeAssignments --transform AlignVariablesSection:up_to_column=4 -c
            # AlignVariablesSection:enabled=True .
            (
                [("NormalizeAssignments", []), ("AlignVariablesSection", ["up_to_column=4"])],
                {"AlignVariablesSection": ["enabled=True"]},
                True,
                "AlignVariablesSection",
            ),
            # robotidy --transform NormalizeAssignments --transform AlignVariablesSection:up_to_column=4 -c
            # AlignVariablesSection:enabled=False .
            (
                [("NormalizeAssignments", []), ("AlignVariablesSection", ["up_to_column=4"])],
                {"AlignVariablesSection": ["enabled=False"]},
                False,
                "AlignVariablesSection",
            ),
        ],
    )
    def test_disable_transformers(
        self, transformers, configure, present, force_order, allow_disabled, test_for, skip_config
    ):
        if force_order and not transformers:
            present = False
        loaded_transformers = load_transformers(
            transformers,
            configure,
            skip=skip_config,
            allow_disabled=allow_disabled,
            force_order=force_order,
            target_version=ROBOT_VERSION.major,
        )
        if present:
            assert any(transformer.name == test_for for transformer in loaded_transformers)
        else:
            assert all(transformer.name != test_for for transformer in loaded_transformers)

    @pytest.mark.parametrize("target_version", [4, 5, None])
    @pytest.mark.parametrize("version", [4, 5])
    @pytest.mark.parametrize(
        "transform, config",
        [
            ([], {}),
            ([("AlignVariablesSection", ["up_to_column=3"])], {"AlignVariablesSection": ["up_to_column=4"]}),
            ([("InlineIf", [])], {}),
            ([("InlineIf", []), ("AlignTemplatedTestCases", [])], {}),
            ([], {"ReplaceReturns": ["enabled=True"]}),
            ([("ReplaceReturns", [])], {"InlineIf": ["enabled=True"]}),
        ],
    )
    def test_overwriting_disabled_in_version(self, target_version, version, transform, config, capsys, skip_config):
        if target_version and target_version > version:
            pytest.skip("Handled by exception")
        warn_with = []
        if transform:
            expected_transformers = []
            for name, args in transform:
                if name in ("ReplaceReturns", "InlineIf") and 4 in (version, target_version):
                    warn_with.append(name)
                else:
                    expected_transformers.append(name)
        else:
            expected_transformers = ["all_default"]
            for name in ("ReplaceReturns", "InlineIf"):
                if config.get(name, "") == "enabled=True" and 4 in (version, target_version):
                    warn_with.append(name)

        if target_version is None:
            target_version = version
        expected_transformers = sorted(expected_transformers)
        mocked_version = Mock(major=version)
        with patch("robotidy.transformers.ROBOT_VERSION", mocked_version):
            transformers = load_transformers(transform, config, skip=skip_config, target_version=target_version)
        transformers_names = sorted([transformer.name for transformer in transformers])
        if expected_transformers == ["all_default"]:
            only_5_found = any(
                name in {"InlineIf", "ReplaceBreakContinue", "ReplaceReturns"} for name in transformers_names
            )
            assert not (target_version == 4 and only_5_found)
        else:
            assert transformers_names == expected_transformers
        if warn_with:
            if target_version == version:
                expected_output = [
                    f"{name} transformer requires Robot Framework 5.* version but you have {mocked_version} installed. "
                    f"Upgrade installed Robot Framework if you want to use this transformer.\n"
                    for name in warn_with
                ]
            else:
                expected_output = [
                    f"{name} transformer requires Robot Framework 5.* version but you set --target-version "
                    f"rf{target_version}. Set --target-version to rf5 or do not forcefully enable this transformer "
                    f"with --transform / enable parameter.\n"
                    for name in warn_with
                ]
            expected_output = "".join(expected_output)
            output = capsys.readouterr()
            assert output.out == expected_output

    @pytest.mark.parametrize(
        "transform, warn_on",
        [
            (["OrderTags"], []),  # not duplicated
            (["OrderTags", "OrderTags"], ["OrderTags"]),
            (["OrderTags", "NormalizeSeparators", "OrderTags"], ["OrderTags"]),
            (
                ["OrderTags", "NormalizeSeparators", "OrderTags", "NormalizeSeparators"],
                ["OrderTags", "NormalizeSeparators"],
            ),
            (["SplitTooLongLine"] * 3, ["SplitTooLongLine"]),  # warn only once
        ],
    )
    def test_duplicated_name_in_transform(self, transform, warn_on, capsys):
        transformers = [(name, []) for name in transform]
        load_transformers(transformers, {}, target_version=ROBOT_VERSION.major)
        expected_output = "".join(
            [
                f"Duplicated transformer '{name}' in the transform option. "
                f"It will be run only once with the configuration from the last transform.\n"
                for name in warn_on
            ]
        )
        output = capsys.readouterr()
        assert output.out == expected_output
