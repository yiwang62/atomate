# coding: utf-8

from __future__ import division, print_function, unicode_literals, absolute_import

import os
import unittest
from monty.serialization import loadfn#, dumpfn
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from pymatgen.core.structure import Molecule
from pymatgen.analysis.graphs import build_MoleculeGraph
from pymatgen.io.qchem.outputs import QCOutput

from atomate.qchem.firetasks.fragmenter import FragmentMolecule
from atomate.qchem.firetasks.parse_outputs import QChemToDb
from atomate.utils.testing import AtomateTest
from pymatgen.analysis.local_env import OpenBabelNN


__author__ = "Samuel Blau"
__email__ = "samblau1@gmail.com"

module_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)))
db_dir = os.path.join(module_dir, "..", "..", "..", "common", "test_files")


class TestFragmentMolecule(AtomateTest):
    @classmethod
    def setUpClass(cls):
        cls.pc = Molecule.from_file(
            os.path.join(module_dir, "..", "..", "test_files", "PC.xyz"))
        cls.pos_pc = Molecule.from_file(
            os.path.join(module_dir, "..", "..", "test_files", "PC.xyz"))
        cls.pos_pc.set_charge_and_spin(charge=1)
        cls.pc_edges = [[5, 10], [5, 12], [5, 11], [5, 3], [3, 7], [3, 4],
                        [3, 0], [4, 8], [4, 9], [4, 1], [6, 1], [6, 0], [6, 2]]
        cls.pc_frag1 = Molecule.from_file(
            os.path.join(module_dir, "..", "..", "test_files", "PC_frag1.xyz"))
        cls.pc_frag1_edges = [[0, 2], [4, 2], [2, 1], [1, 3]]
        cls.tfsi = Molecule.from_file(os.path.join(module_dir, "..", "..", "test_files", "TFSI.xyz"))
        cls.neg_tfsi = Molecule.from_file(os.path.join(module_dir, "..", "..", "test_files", "TFSI.xyz"))
        cls.neg_tfsi.set_charge_and_spin(charge=-1)
        cls.tfsi_edges = [14,1],[1,4],[1,5],[1,7],[7,11],[7,12],[7,13],[14,0],[0,2],[0,3],[0,6],[6,8],[6,9],[6,10]

    def setUp(self, lpad=False):
        super(TestFragmentMolecule, self).setUp(lpad=False)

    def tearDown(self):
        pass

    def _test_edges_given_PC(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.pc, edges=self.pc_edges, depth=0, open_rings=False)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 295 * 3)

    def _test_edges_given_PC_frag1(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(
                molecule=self.pc_frag1, edges=self.pc_frag1_edges, depth=0)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 12 * 3)

    def _test_babel_PC_frag1(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.pc_frag1, depth=0)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 12 * 3)

    def _test_edges_given_TFSI(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.tfsi, edges=self.tfsi_edges, depth=0)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 468)

    def _test_babel_TFSI(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.tfsi, depth=0)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 468)

    def _test_neg_TFSI_with_additional_charge_separation(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.neg_tfsi, depth=0, allow_additional_charge_separation=True)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 624)

    def _test_neg_TFSI_without_additional_charge_separation(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.neg_tfsi, depth=0, allow_additional_charge_separation=False)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 312)

    def _test_build_unique_relevant_molecules(self):
        ft = FragmentMolecule(molecule=self.pc, edges=self.pc_edges, depth=0)
        ft.mol = ft.get("molecule")
        ft.depth = ft.get("depth")
        ft.charges = [-1, 0, 1]
        mol_graph = build_MoleculeGraph(self.pc, edges=self.pc_edges)
        ft.unique_fragments = mol_graph.build_unique_fragments()
        ft._build_unique_relevant_molecules()
        self.assertEqual(len(ft.unique_molecules), 295 * 3)
        # dumpfn(ft.unique_molecules, os.path.join(module_dir,"pc_mols.json"))
        ref_mols = loadfn(os.path.join(module_dir, "pc_mols.json"))
        self.assertEqual(ft.unique_molecules, ref_mols)

        ft = FragmentMolecule(molecule=self.pos_pc, edges=self.pc_edges, depth=0)
        ft.mol = ft.get("molecule")
        ft.depth = ft.get("depth")
        ft.charges = [-1, 0, 1, 2]
        mol_graph = build_MoleculeGraph(self.pos_pc, edges=self.pc_edges)
        ft.unique_fragments = mol_graph.build_unique_fragments()
        ft._build_unique_relevant_molecules()
        self.assertEqual(len(ft.unique_molecules), 295 * 4)
        # dumpfn(ft.unique_molecules, os.path.join(module_dir,"pos_pc_mols.json"))
        ref_mols = loadfn(os.path.join(module_dir, "pos_pc_mols.json"))
        self.assertEqual(ft.unique_molecules, ref_mols)

        ft = FragmentMolecule(molecule=self.pc_frag1, edges=self.pc_frag1_edges, depth=0)
        ft.mol = ft.get("molecule")
        ft.depth = ft.get("depth")
        ft.charges = [-1, 0, 1]
        mol_graph = build_MoleculeGraph(self.pc_frag1, edges=self.pc_frag1_edges)
        ft.unique_fragments = mol_graph.build_unique_fragments()
        ft._build_unique_relevant_molecules()
        self.assertEqual(len(ft.unique_molecules), 12 * 3)
        # dumpfn(ft.unique_molecules, os.path.join(module_dir,"pc_frag1_mols.json"))
        ref_mols = loadfn(os.path.join(module_dir, "pc_frag1_mols.json"))
        self.assertEqual(ft.unique_molecules, ref_mols)

    def _test_build_new_FWs(self):
        ft = FragmentMolecule(molecule=self.pc_frag1, edges=self.pc_frag1_edges, depth=0)
        ft.mol = ft.get("molecule")
        ft.depth = ft.get("depth")
        ft.charges = [-1, 0, 1]
        mol_graph = build_MoleculeGraph(self.pc_frag1, edges=self.pc_frag1_edges)
        ft.unique_fragments = mol_graph.build_unique_fragments()
        ft._build_unique_relevant_molecules()
        ft.all_relevant_docs = list()
        new_FWs = ft._build_new_FWs()
        self.assertEqual(len(new_FWs), 36)

    def _test_in_database_through_build_new_FWs(self):
        ft = FragmentMolecule(molecule=self.pc_frag1, edges=self.pc_frag1_edges, depth=0)
        ft.mol = ft.get("molecule")
        ft.depth = ft.get("depth")
        ft.charges = [-1, 0, 1]
        mol_graph = build_MoleculeGraph(self.pc_frag1, edges=self.pc_frag1_edges)
        ft.unique_fragments = mol_graph.build_unique_fragments()
        ft._build_unique_relevant_molecules()
        ft.all_relevant_docs = loadfn(os.path.join(module_dir, "doc.json"))
        new_FWs = ft._build_new_FWs()
        self.assertEqual(len(new_FWs), 29)

    def _test_in_database_with_actual_database(self):
        db_file=os.path.join(db_dir, "db.json")
        dir2620=os.path.join(module_dir, "..", "..", "test_files", "2620_complete")
        mol2620=QCOutput(os.path.join(dir2620,"mol.qout.opt_0")).data["initial_molecule"]
        parse_firetask = QChemToDb(calc_dir=dir2620, db_file=db_file)
        parse_firetask.run_task({})
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.neg_tfsi, db_file=db_file, depth=0, allow_additional_charge_separation=True)
            ft.run_task({})
            self.assertEqual(ft.check_db,True)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 623)
            self.assertEqual(ft._in_database(mol2620),True)
            mol2620.set_charge_and_spin(charge=0)
            self.assertEqual(ft._in_database(mol2620),False)

    def _test_babel_PC_with_RO_depth_0_vs_depth_10(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.pc, depth=0, open_rings=True)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            depth0frags = ft.unique_fragments
            self.assertEqual(len(depth0frags), 509)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 1527)

        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.pc, depth=10, open_rings=True)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            depth10frags = ft.unique_fragments
            fragments_by_level = ft.fragments_by_level
            self.assertEqual(len(depth10frags), 509)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 1513)

        num_frags_by_level = [13,51,95,115,105,75,39,14,2,0]
        for ii in range(10):
            self.assertEqual(len(fragments_by_level[str(ii)]),num_frags_by_level[ii])

        for fragment10 in depth10frags:
            found = False
            for fragment0 in depth0frags:
                if fragment0.isomorphic_to(fragment10):
                    found = True
            self.assertEqual(found, True)

    def _test_babel_PC_depth_0_vs_depth_10(self):
        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.pc, depth=0, open_rings=False)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            depth0frags = ft.unique_fragments
            self.assertEqual(len(depth0frags), 295)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 295*3)

        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.pc, depth=10, open_rings=False)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            depth10frags = ft.unique_fragments
            fragments_by_level = ft.fragments_by_level
            self.assertEqual(len(depth10frags), 63)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 63*3)

        num_frags_by_level = [8,12,15,14,9,4,1]
        for ii in range(7):
            self.assertEqual(len(fragments_by_level[str(ii)]),num_frags_by_level[ii])

        for fragment10 in depth10frags:
            found = False
            for fragment0 in depth0frags:
                if fragment0.isomorphic_to(fragment10):
                    found = True
            self.assertEqual(found, True)

    def test_weird(self):

        with patch("atomate.qchem.firetasks.fragmenter.FWAction"
                   ) as FWAction_patch:
            ft = FragmentMolecule(molecule=self.pc, depth=10, open_rings=False)
            ft.run_task({})
            self.assertEqual(ft.check_db,False)
            depth10frags = ft.unique_fragments
            fragments_by_level = ft.fragments_by_level
            self.assertEqual(len(depth10frags), 63)
            self.assertEqual(
                len(FWAction_patch.call_args[1]["additions"]), 63*3)


if __name__ == "__main__":
    unittest.main()
