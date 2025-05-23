# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import streamlit as st

from llama_stack.distribution.ui.modules.api import llama_stack_api


def benchmarks():
    """
    Inspect registered benchmarks and display details for a selected one.
    """
    st.header("Benchmarks")

    # Fetch and check benchmarks
    bm_list = llama_stack_api.client.benchmarks.list()
    if not bm_list:
        st.info("No benchmarks available.")
        return
    benchmarks_info = {d.identifier: d.to_dict() for d in bm_list}

    # Let user select and view a benchmark
    selected_benchmark = st.selectbox(
        "Select an eval task", list(benchmarks_info.keys()), key="benchmark_inspect"
    )
    st.json(benchmarks_info[selected_benchmark], expanded=True)
