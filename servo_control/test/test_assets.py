# Copyright 2026 Alexandru Gheorghita
#
# Use of this source code is governed by an MIT-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/MIT.
"""Verify that the Gazebo world and its model are self-contained."""

from pathlib import Path
import xml.etree.ElementTree as ElementTree


PACKAGE_ROOT = Path(__file__).parents[1]
MODEL_ROOT = PACKAGE_ROOT / 'models' / 'Servomotor'


def test_world_references_packaged_model():
    world = ElementTree.parse(PACKAGE_ROOT / 'worlds' / 'lab_world.sdf')
    model_uris = [element.text for element in world.findall('.//include/uri')]

    assert 'model://Servomotor' in model_uris
    assert MODEL_ROOT.is_dir()


def test_model_config_and_meshes_exist():
    model_config = ElementTree.parse(MODEL_ROOT / 'model.config')
    sdf_name = model_config.findtext('./sdf')

    assert sdf_name
    sdf_path = MODEL_ROOT / sdf_name
    assert sdf_path.is_file()

    model = ElementTree.parse(sdf_path)
    mesh_uris = [element.text for element in model.findall('.//mesh/uri')]
    assert mesh_uris

    for uri in mesh_uris:
        prefix = 'model://Servomotor/'
        assert uri.startswith(prefix)
        assert (MODEL_ROOT / uri.removeprefix(prefix)).is_file()
