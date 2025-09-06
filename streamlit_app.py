#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuantMuse Trading Platform - Streamlit Cloud Entry Point
"""

# Import the main dashboard application
try:
    from professional_dashboard import *
except ImportError as e:
    import streamlit as st
    st.error(f"Failed to import main dashboard: {e}")
    st.info("Please check that all dependencies are properly installed.")