import streamlit as st
import pandas as pd
from argparse import Namespace
import vast_utils
import os

def get_instances():
    """Fetches instances from the Vast.ai API."""
    api_key = vast_utils.get_api_key()
    if not api_key:
        st.error("Vast.ai API key not found. Please set it up by creating the file ~/.config/vastai/vast_api_key with your API key.")
        return None

    args = Namespace(url=vast_utils.server_url_default, api_key=api_key, raw=True, retry=3)
    vast_utils.headers["Authorization"] = f"Bearer {api_key}"

    try:
        instances = vast_utils.show_instances(args)
        return instances
    except Exception as e:
        st.error(f"Error fetching instances: {e}")
        return None

def main():
    st.set_page_config(layout="wide")
    st.title("VastAI Wizard")

    # --- Instance Dashboard ---
    st.header("Instance Dashboard")
    if 'instances' not in st.session_state:
        st.session_state.instances = get_instances()

    if st.button("Refresh Instances"):
        st.session_state.instances = get_instances()

    instances = st.session_state.instances
    if instances is not None:
        if not instances:
            st.info("No active instances found.")
        else:
            df_instances = pd.DataFrame(instances)
            st.dataframe(df_instances)
            for i, row in df_instances.iterrows():
                if st.button(f"Destroy {row['id']}", key=f"destroy_{row['id']}"):
                    st.warning(f"Destroying instance {row['id']}...")
                    api_key = vast_utils.get_api_key()
                    args = Namespace(url=vast_utils.server_url_default, api_key=api_key, raw=True, retry=3)
                    vast_utils.headers["Authorization"] = f"Bearer {api_key}"
                    try:
                        result = vast_utils.destroy_instance(args, row['id'])
                        if result.get('success'):
                            st.success(f"Instance {row['id']} destroyed.")
                            st.session_state.instances = get_instances()
                            st.experimental_rerun()
                        else:
                            st.error(f"Failed to destroy instance {row['id']}: {result.get('msg')}")
                    except Exception as e:
                        st.error(f"Error destroying instance {row['id']}: {e}")

    # --- Create Instance Wizard ---
    st.header("Create Instance Wizard")

    provisioning_scripts = [f for f in os.listdir('.') if f.endswith('.sh')]

    with st.form("create_instance_form"):
        st.write("Search for an instance to rent:")
        gpu_name = st.text_input("GPU Name (e.g., RTX 4090)", "RTX 4090")
        num_gpus = st.number_input("Number of GPUs", min_value=1, value=1)
        disk_space = st.number_input("Disk Space (GB)", min_value=10, value=20)

        selected_script = st.selectbox("Provisioning Script", provisioning_scripts)

        submitted = st.form_submit_button("Find Machines")
        if submitted:
            query = f"gpu_name={gpu_name.replace(' ', '_')} num_gpus={num_gpus} disk_space>={disk_space} rentable=true"
            st.session_state.search_results = None
            try:
                api_key = vast_utils.get_api_key()
                args = Namespace(url=vast_utils.server_url_default, api_key=api_key, raw=True, retry=3, order='dph_total', type='on-demand', limit=10)
                vast_utils.headers["Authorization"] = f"Bearer {api_key}"
                search_results = vast_utils.search_offers(args, query)
                st.session_state.search_results = search_results
                st.session_state.selected_script = selected_script
            except Exception as e:
                st.error(f"Error searching for offers: {e}")

    if 'search_results' in st.session_state and st.session_state.search_results:
        st.subheader("Search Results")
        df_offers = pd.DataFrame(st.session_state.search_results)
        st.dataframe(df_offers)

        for i, row in df_offers.iterrows():
            if st.button(f"Rent Instance {row['id']}", key=f"rent_{row['id']}"):
                st.info(f"Attempting to rent instance {row['id']}...")
                try:
                    with open(st.session_state.selected_script, 'r') as f:
                        onstart_script = f.read()

                    api_key = vast_utils.get_api_key()
                    create_args = Namespace(
                        url=vast_utils.server_url_default,
                        api_key=api_key,
                        retry=3,
                        onstart=None,
                        onstart_cmd=onstart_script,
                        image="nvidia/cuda:12.1.0-base-ubuntu22.04",
                        disk=disk_space,
                        label=f"wizard_{row['id']}",
                        login=None,
                        python_utf8=False, lang_utf8=False, use_jupyter_lab=False,
                        jupyter_dir=None, jupyter=False, ssh=True, direct=True,
                        env='', args=None, bid_price=None,
                        force=False, cancel_unavail=False
                    )
                    vast_utils.headers["Authorization"] = f"Bearer {api_key}"

                    result = vast_utils.create_instance(create_args, row['id'])

                    if result.get('success'):
                        st.success(f"Instance {result['new_contract_id']} created successfully!")
                        st.session_state.instances = get_instances()
                        st.experimental_rerun()
                    else:
                        st.error(f"Failed to create instance: {result.get('msg', 'Unknown error')}")

                except Exception as e:
                    st.error(f"An error occurred during instance creation: {e}")


if __name__ == "__main__":
    main()
