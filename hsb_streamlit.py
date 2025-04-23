import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

def process_hsb(file, omschrijving):
    data = []

    with pdfplumber.open(file) as pdf:
        factuurnummer = ''
        factuurdatum = ''
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()

            if i == 0:  

                date_match = re.search(r'Factuurdatum\s+(\d{2}-\d{2}-\d{4})', text)
                factuurdatum = date_match.group(1) if date_match else None

                factuurnummer_match = re.search(r'Factuurnummer\s+([\d\.]+)', text)
                factuurnummer = factuurnummer_match.group(1) if factuurnummer_match else None

            lines = text.split('\n')

            current_kenteken = None
            current_bedrag = None
            geldig_vanaf = ''
            geldig_tot = ''

            for line in lines:

                kenteken_match = re.match(
                    r'([A-Z0-9\-]{6,})\s+[-\d\.,]+\s+\w+\s+[-\d\.,]+\s+\d+%\s+([-\d\.,]+)', 
                    line
                )

                if kenteken_match:
                    current_kenteken = kenteken_match.group(1)
                    current_bedrag = kenteken_match.group(2).replace(',', '')


                periode_match = re.search(
                    r'Periode van (\d{2}-\d{2}-\d{4}) tot en met (\d{2}-\d{2}-\d{4})', 
                    line
                )

                if periode_match and current_kenteken and current_bedrag:
                    geldig_vanaf = periode_match.group(1)
                    geldig_tot = periode_match.group(2)


                    data.append({
                        'Factuurnummer': factuurnummer,
                        'Factuurdatum': factuurdatum,
                        'Kenteken': current_kenteken,
                        'Geldig vanaf': geldig_vanaf,
                        'Geldig tot': geldig_tot,
                        'Bedrag': float(current_bedrag)
                    })

                    current_kenteken = None
                    current_bedrag = None


    factuur = pd.DataFrame(data)


    factuur['Factuurdatum'] = pd.to_datetime(factuur['Factuurdatum'], format='%d-%m-%Y')  
    factuur['Boekjaar'] = factuur['Factuurdatum'].dt.year              
    factuur['Periode'] = factuur['Factuurdatum'].dt.month              
    factuur['Factuurdatum'] = factuur['Factuurdatum'].dt.strftime('%d-%m-%Y')  

    #######
    # Plaats factuur in juiste format
    #######

    columns = [
        'Dagboek: Code', 'Boekjaar', 'Periode', 'Boekstuknummer', 'Omschrijving: Kopregel', 
        'Factuurdatum', 'Vervaldatum', 'Valuta', 'Wisselkoers', 'Betalingsvoorwaarde: Code', 
        'Ordernummer', 'Uw ref.', 'Betalingsreferentie', 'Code', 'Naam', 'Grootboekrekening', 
        'Omschrijving', 'BTW-code', 'BTW-percentage', 'Bedrag', 'Aantal', 'BTW-bedrag', 
        'Opmerkingen', 'Project', 'Van', 'Naar', 'Kostenplaats: Code', 'Kostenplaats: Omschrijving', 
        'Kostendrager: Code', 'Kostendrager: Omschrijving'
    ]

    import_df = pd.DataFrame(columns=columns)

    import_df['Boekjaar'] = factuur['Boekjaar'] 
    import_df['Dagboek: Code'] = 60                  
    import_df['Periode'] = factuur['Periode']                  
    import_df['Factuurdatum'] = factuur['Factuurdatum']   
    import_df['Omschrijving: Kopregel'] = omschrijving
    import_df['Omschrijving'] = omschrijving
    import_df['Uw ref.'] = factuur['Factuurnummer'] 
    import_df['Code'] = 292
    import_df['Grootboekrekening'] = 7520
    import_df['Bedrag'] = factuur['Bedrag'] 
    import_df['Van'] = factuur['Geldig vanaf'] 
    import_df['Naar'] = factuur['Geldig tot'] 
    import_df['Kostenplaats: Code'] = factuur['Kenteken'] 
    import_df['Kostenplaats: Omschrijving'] = factuur['Kenteken'] 

    # Voeg een extra eerste rij toe, want deze wordt niet meegenomen in de import
    new_row = import_df.iloc[0].copy() 
    new_row['Bedrag'] = ''
    new_row['Kostenplaats: Code'] = ''
    new_row['Kostenplaats: Omschrijving'] = ''
    import_df = pd.concat([pd.DataFrame([new_row]), import_df], ignore_index=True)

    return import_df


def main():
    st.title('PDF naar Excel: Factuur HSB')

    uploaded_file = st.file_uploader('Upload een PDF bestand', type='pdf')
    omschrijving = st.text_input('Voer de omschrijving in:', 'HSB april 2025(1)')

    if uploaded_file is not None:
        df = process_hsb(uploaded_file, omschrijving)
        
        st.write('Verwerkte gegevens:', df.head())

        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(label='Download het Excel bestand', data=output, file_name=f'{omschrijving} factuur.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    main()