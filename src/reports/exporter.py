import pandas as pd
from pandas import DataFrame


def export_excel(
    df: DataFrame = None, header_colors: dict = {}, file=None, sheet_name=""
):
    """
    > The function takes a DataFrame and a dictionary of header colors and writes the DataFrame to an
    Excel file with the header row colored according to the dictionary

    :param df: The DataFrame to export to Excel
    :type df: DataFrame
    :param header_colors: a dictionary of parameters for the header color
    :type header_colors: dict
    :param file: The name of the file to save the dataframe to
    :return: A dataframe with the columns:

    AJAY, 01.02.2023
    """

    if df is None or file is None:
        return

    writer = pd.ExcelWriter(file, engine="xlsxwriter")
    df.to_excel(writer, sheet_name="Employee", startrow=1, header=False, index=False)
    workbook = writer.book
    worksheet = writer.sheets["Employee"]

    # Add a header format.
    header_format = workbook.add_format(
        {
            "bold": True,
            "text_wrap": True,
            "valign": "top",
            "fg_color": header_colors.get("fg_color", "#D7E4BC"),
            "border": 1,
        }
    )

    # Write the column headers with the defined format.
    for col_num, value in enumerate(df.columns.values):
        worksheet.write(0, col_num, value, header_format)

    # Close the Pandas Excel writer and output the Excel file.
    writer.close()
