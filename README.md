# BankArchives
Only German banks with FINTS access and PIN/TAN authentication
# Features
* Storing account statements, securities account data
 * Storing historical stock prices from Yahoo! Finance or AlphaVantage
 * Transfers and appointment transfers
 * Depot and historical price data evaluations
# Free registrations
 * Request a free HBCI-ZKA registration key https://www.hbci-zka.de/
 * Request a free API key https://www.alphavantage.co/support/#support
# Installing on Windows
* Install MariaDB 10.5 and create an empty database >banken<
* Install Python 3.9
* Download GitHub project from https://github.com/WolfgangKramer/BankArchive
The directory structure, should look like this:  
<pre>
bankarchive/  

|-- BANKEN
|	|-- src
|		|-- banking
|   			|-- __init__.py
|   			|-- bank.py
|			...
|   			|-- utils.py
|		|-- data
|			|-- background.gif
|			|-- Banking.py
</pre>
# Install Requirements
pip install -r requirements.txt  
# Create BAT file Banking.bat
> cd C:\BANKEN\src\data  
> py Banking.py
# Customizing
1. Customize Application INI File
2. Import Bankidentifier Data (Bankleitzahlendateien ungepackt)
3. Import FINTS Server Data
4. Create your Banks
# Banks in testing phase
 * BMW Bank (not tested securities account data)
 * Consors 
 * Flatexdegiro Bank AG
 * VR Bank (not tested securities account data)
