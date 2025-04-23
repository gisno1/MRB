import streamlit as st
import pdfplumber
import pandas as pd
import io
import re

def process_eurovignet(file):
    data = []

    with pdfplumber.open(file) as pdf:
        factuurnummer = ''
        factuurdatum = ''
        maand = ''
        
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()

            if i == 0:
                date_match = re.search(r'Datum\s+(\d{2}-\d{2}-\d{4})', text)
                factuurdatum = date_match.group(1) if date_match else None

                kenmerk_match = re.search(r'Kenmerk\s+([A-Z]{3} \d{6})', text)
                factuurnummer = kenmerk_match.group(1) if kenmerk_match else None

                maand_match = re.search(r'Betreft: Maandoverzicht (\w+) \d{4}', text)
                maand = maand_match.group(1).upper() if maand_match else 'Onbekende maand'

            elif i > 0:
                lines = text.split('\n')

                for line in lines:
                    match = re.search(
                        r'(\d{2}-\d{2}-\d{2})\s+\d+\s+#?\s?[A-Z]{0,2}\s?([A-Z0-9-]{5,})'  # Datum + kenteken
                        r'(?:\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}-\d{2}-\d{2}))?'             # Geldig vanaf / t/m optioneel
                        r'.*?€\s?([-\d\.,]+)',                                           # Bedrag
                        line
                    )

                    if match:
                        aangifte_datum = match.group(1)
                        kenteken = match.group(2)
                        geldig_vanaf = match.group(3) if match.group(3) else ''
                        geldig_tot = match.group(4) if match.group(4) else ''
                        bedrag = match.group(5).replace('.', '').replace(',', '.') 

                        data.append({
                            'Factuurnummer': factuurnummer,
                            'Factuurdatum': factuurdatum,
                            'Maand': maand,
                            'Aangifte datum': aangifte_datum,
                            'Kenteken': kenteken,
                            'Geldig vanaf': geldig_vanaf,
                            'Geldig tot': geldig_tot,
                            'Bedrag': float(bedrag)
                        })

    factuur = pd.DataFrame(data)

    factuur['Kenteken'] = factuur['Kenteken'].apply(lambda x: re.sub(r'(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])', '-', x))

    factuur['Factuurdatum'] = pd.to_datetime(factuur['Factuurdatum'], format='%d-%m-%Y')  
    factuur['Boekjaar'] = factuur['Factuurdatum'].dt.year              
    factuur['Periode'] = factuur['Factuurdatum'].dt.month              
    factuur['Factuurdatum'] = factuur['Factuurdatum'].dt.strftime('%d-%m-%Y')  

    factuur['Geldig vanaf'] = pd.to_datetime(factuur['Geldig vanaf'], format='%d-%m-%y', errors='coerce')
    factuur['Geldig tot'] = pd.to_datetime(factuur['Geldig tot'], format='%d-%m-%y', errors='coerce')

    factuur['Geldig vanaf'] = factuur['Geldig vanaf'].dt.strftime('%d-%m-%Y')
    factuur['Geldig tot'] = factuur['Geldig tot'].dt.strftime('%d-%m-%Y')

    # Plaats factuur in juiste format
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
    import_df['Omschrijving: Kopregel'] = factuur['Factuurnummer'] + ' / BELASTING'
    import_df['Omschrijving'] = factuur['Factuurnummer'] + ' / BELASTING' + ' / ' + factuur['Maand']
    import_df['Uw ref.'] = factuur['Factuurnummer'] 
    import_df['Code'] = 200144
    import_df['Grootboekrekening'] = 7530
    import_df['Bedrag'] = factuur['Bedrag'] 
    import_df['Van'] = factuur['Geldig vanaf'] 
    import_df['Naar'] = factuur['Geldig tot'] 
    import_df['Kostenplaats: Code'] = factuur['Kenteken'] 
    import_df['Kostenplaats: Omschrijving'] = factuur['Kenteken'] 

    # Voeg een extra eerste rij toe
    new_row = import_df.iloc[0].copy() 
    new_row['Bedrag'] = ''
    new_row['Kostenplaats: Code'] = ''
    new_row['Kostenplaats: Omschrijving'] = ''
    import_df = pd.concat([pd.DataFrame([new_row]), import_df], ignore_index=True)

    return import_df


def main():
    st.title('PDF naar Excel: Factuur eurovignet')

    uploaded_file = st.file_uploader('Upload een PDF bestand', type='pdf')

    if uploaded_file is not None:
        df = process_eurovignet(uploaded_file)
        
        # Toon de data
        st.write('Verwerkte gegevens:', df.head())

        # Laat de gebruiker het bestand downloaden
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)

        st.download_button(label='Download het Excel bestand', data=output, file_name='eurovignet factuur.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    main()
