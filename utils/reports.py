import os.path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import os

def print_results(report_name=None, model_name=None):
    fname = f"{report_name}.{model_name.replace(':','-')}.xlsx"
    results_table = pd.read_excel(fname)

    # Generate trl_completeness plot and table
    plt1, trl_table = trl_completeness(results_table)

    # Generate persona_completeness plot and table
    plt2, persona_table = persona_completeness(results_table)


    # Save figures and tables to PDF
    with PdfPages(report_name + '.' + model_name.replace(':','-') + '.pdf') as pdf:
        # Save persona_completeness plot
        pdf.savefig(plt1)
        """
        # Save persona_completeness table
        fig, ax = plt.subplots()
        ax.axis('off')
        ax.table(cellText=trl_table.values, colLabels=trl_table.columns, loc='center')
        pdf.savefig(fig)
        plt.close()
        """
        # Save trl_completeness plot
        pdf.savefig(plt2)

        """
        # Save trl_completeness table
        fig, ax = plt.subplots()
        ax.axis('off')
        ax.table(cellText=persona_table.values, colLabels=persona_table.columns, loc='center')
        pdf.savefig(fig)
        plt.close()
        """
    plt1.savefig(report_name + '.' + model_name.replace(':', '-') + '_trl.svg', format='svg')
    plt2.savefig(report_name + '.' + model_name.replace(':', '-') + '_persona.svg', format='svg')

    print("PDF report generated successfully.")

def trl_completeness(results_table=None):
    if results_table is None:
        print("Please provide a valid DataFrame.")
        return

    results_table['TRL'] = results_table['TRL'].astype(int)

    grouped = results_table \
        .groupby('TRL') \
        .agg({'Binary': lambda x: (x == 'YES').sum(), 'Q': 'count'}) \
        .reset_index()
    grouped.columns = ['TRL', 'Complete', 'Total']

    # Calculate 'FREQ'
    grouped['FREQ'] = ((grouped['Complete'] / grouped['Total']) * 100 ) + 1  # Add 1 so they all register
    grouped.sort_values(by=['TRL'], ascending=False, inplace=True)

    # Colorblind friendly colors
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22',
              '#6fcc9f']

    # offset_copy works for polar plots also.
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})
    fig.suptitle('Completeness by Technology Readiness Level (TRL)')

    ax.barh(grouped['TRL'], np.radians(grouped['FREQ'] * 0.01 * 360), color=colors, label=grouped['TRL'])
    # Plot each TRL with corresponding color and alpha
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)
    ax.set_thetagrids(range(0, 360, 36), labels=range(0, 100, 10))
    # ax.set_rlabel_position(-5)
    # ax.set_rgrids(grouped['TRL'], labels=grouped['TRL'])
    ax.set_rgrids(grouped['TRL'], labels=[])
    ax.legend(title='TRL', bbox_to_anchor=(0., 1.), loc='upper right')
    grouped['TRL'] = grouped['TRL'].astype(int)
    grouped['Complete'] = grouped['Complete'].astype(int)
    grouped['Total'] = grouped['Total'].astype(int)

    return fig, grouped.round({'FREQ': 1})

def persona_completeness(results_table=None):
    if results_table is None:
        print("Please provide a valid DataFrame.")
        return

    grouped = results_table \
        .groupby('Agent') \
        .agg({'Binary': lambda x: (x == 'YES').sum(), 'Q': 'count'}) \
        .reset_index()
    grouped.columns = ['Agent', 'Complete', 'Total']

    # Calculate 'FREQ'
    grouped['FREQ'] = (grouped['Complete'] / grouped['Total']) * 100
    grouped.sort_values(by=['FREQ'], ascending=False, inplace=True)

    # Number of rows and columns for subplots
    num_cols = 5
    num_rows = np.ceil(len(grouped) / num_cols).astype(int)

    # Create subplots grid
    fig, ax = plt.subplots(num_rows, num_cols, figsize=(12, 6))

    fig.suptitle('Completeness by Agent')

    # Flatten axes for easier indexing
    ax = ax.flatten()

    for i, row in grouped.iterrows():
        size = 0.3
        vals = [row['FREQ'], 100 - row['FREQ']]

        ax[i].pie(vals, radius=1, colors=['#4CAF50', '#E0E0E0'], wedgeprops=dict(width=size, edgecolor='w'))
        ax[i].text(0, 0, f"{row['FREQ']:.0f}%", ha='center', va='center', fontsize=14)
        ax[i].set_title(row['Agent'], pad=0)

    # Hide unused subplots if any
    for j in range(grouped.shape[0], len(ax)):
        fig.delaxes(ax[j])

    return fig, grouped.round({'FREQ': 0})


if __name__ == '__main__':
    print_results(report_name='../synthetics/Complete.character.llama3-70b', model_name='character')

