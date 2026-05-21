=========================================================================================================
====================== INSTRUKCJA UPGRADU CBR-8 DO WERSJI 17.12.1z4 –  ==================================
=========================================================================================================


CMTS-y do upgrade'u:
- pl-bzg01a-br05
- pl-bzg01a-br06

Oficjalna dokumentacja Cisco:
https://www.cisco.com/c/en/us/td/docs/cable/cbr/upgrade/guide/b_cbr_upgrade_17_12/m_17_12_1z2_upgrade.html

Plik oprogramowania: cbrsup-universalk9.17.12.01z4.SPA.bin
MD5: e2257b800c725833b1a2f0052bc98103

==================================================================================================================================================================
1. PRZYGOTOWANIE – OTWÓRZ KONSOLE
==================================================================================================================================================================

# pl-bzg01a-br05
telnet pl-bzg01a-rm01 2028   ← Console SUP0 (slot 4)
telnet pl-bzg01a-rm01 2044   ← Console SUP1 (slot 5)
Wykonano: pl-bzg01a-br05 [_]

# pl-bzg01a-br06
telnet pl-bzg01a-rm01 2058   ← Console SUP0 (slot 4)
telnet pl-bzg01a-rm01 2059   ← Console SUP1 (slot 5)
Wykonano: pl-bzg01a-br06 [_]

==================================================================================================================================================================
2. WERYFIKACJA WYMAGAŃ MINIMALNYCH
==================================================================================================================================================================

terminal length 0
show platform diag | i "Slot: SUP|CPLD version|Rommon version|micro|fpga"
show hw-module all fpd
show platform
show platform diag | i fpga
Wykonano: pl-bzg01a-br05 [x]  pl-bzg01a-br06 [x]

Wymagane minimum:
- Supervisor CPLD (SUP-250G): 190717E1
- Supervisor ROMMON: 16.7(9r)S
- Line Card CPLD: 00000026
- Gemini2 Micro: 3.1A
- Gemini2 Apollo FPGA: 4.484F

────────────────────────────────────────────
pl-bzg01a-br05 – Wyniki weryfikacji:
────────────────────────────────────────────
pl-bzg01a-br05#terminal length 0
pl-bzg01a-br05#$i "Slot: SUP|CPLD version|Rommon version|micro|fpga"
        CPLD version                : 00000043
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000043
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 190717E1
        ViperSO CPLD version        : 15111401
        ViperSIO CPLD version       : 15111301
        Rommon version              : 17.15(1r)S
        SUP-PIC CPLD version        : 16051301
        SUP-DC CPLD version         : 15092508
        CPLD version                : 190717E1
        ViperSO CPLD version        : 15111401
        ViperSIO CPLD version       : 15111301
        Rommon version              : 16.7(9r)S
        SUP-PIC CPLD version        : 16051301
        SUP-DC CPLD version         : 15092508
pl-bzg01a-br05#show hw-module all fpd

==== ====================== ====== =============================================
                             H/W   Field Programmable   Current   Min. Required
Slot Card Type               Ver.  Device: "ID-Name"    Version      Version
==== ====================== ====== ================== =========== ==============
 0/1 CBR-RF-PROT-PIC         5.0   35-CBR STEALTHSTAR     7.30        7.13
---- ---------------------- ------ ------------------ ----------- --------------
 1/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 2/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 3/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 4/1 CBR-2X100G-PIC          2.0   55-CBR SUPVE PIC       2.88        2.88
---- ---------------------- ------ ------------------ ----------- --------------
 5/1 CBR-2X100G-PIC          2.0   55-CBR SUPVE PIC       2.88        2.88
---- ---------------------- ------ ------------------ ----------- --------------
 6/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 7/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 8/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 9/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
==== ====================== ====== =============================================


pl-bzg01a-br05#show platform
Chassis type: CBR-8-CCAP-CHASS

Slot      Type                State                 Insert time (ago)
--------- ------------------- --------------------- -----------------
0         CBR-CCAP-LC-40G     ok                    6w2d
0/1       CBR-RF-PROT-PIC     ok                    6w2d
1         CBR-CCAP-LC-40G     ok                    6w2d
1/1       CBR-RF-PIC          ok                    6w2d
2         CBR-CCAP-LC-40G     ok                    6w2d
2/1       CBR-RF-PIC          ok                    6w2d
3         CBR-CCAP-LC-40G     ok                    6w2d
3/1       CBR-RF-PIC          ok                    6w2d
6         CBR-CCAP-LC-40G     ok                    6w2d
6/1       CBR-RF-PIC          ok                    6w2d
7         CBR-CCAP-LC-40G     ok                    6w2d
7/1       CBR-RF-PIC          ok                    6w2d
8         CBR-CCAP-LC-40G     ok                    6w2d
8/1       CBR-RF-PIC          ok                    6w2d
9         CBR-CCAP-LC-40G     ok                    6w2d
9/1       CBR-RF-PIC          ok                    6w2d
SUP0      CBR-SUP-250G        inserted              6w2d
 R0                           ok, active
 F0                           ok, active
 4                            ok, active
 4/1      CBR-2X100G-PIC      ok                    6w2d
SUP1      CBR-SUP-250G        inserted              6w2d
 R1                           ok, standby
 F1                           ok, standby
 5                            ok, standby
 5/1      CBR-2X100G-PIC      ok                    6w2d
P0        CBR-AC-PS           ok                    6w2d
P1        CBR-AC-PS           ok                    6w2d
P2        CBR-AC-PS           ok                    6w2d
P3        CBR-AC-PS           ok                    6w2d
P4        CBR-AC-PS           ok                    6w2d
P5        CBR-AC-PS           ok                    6w2d
P10       CBR-FAN-ASSEMBLY    ok                    6w2d
P11       CBR-FAN-ASSEMBLY    ok                    6w2d
P12       CBR-FAN-ASSEMBLY    ok                    6w2d
P13       CBR-FAN-ASSEMBLY    ok                    6w2d
P14       CBR-FAN-ASSEMBLY    ok                    6w2d

Slot      CPLD Version        Rommon Version
--------- ------------------- ---------------------------------------
0         00000043            2011.03.18
1         00000043            2011.03.18
2         00000026            2011.03.18
3         00000026            2011.03.18
6         00000026            2011.03.18
7         00000026            2011.03.18
8         00000026            2011.03.18
9         00000026            2011.03.18
SUP0      190717E1            17.15(1r)S
SUP1      190717E1            16.7(9r)S

pl-bzg01a-br05#show platform diag | i fpga
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F


=== PORÓWNANIE FIRMWARE vs WYMAGANE MINIMUM (br05) ===

Komponent                        | Wymagane       | Aktualne          | Status
---------------------------------|----------------|-------------------|--------
Supervisor CPLD (SUP-250G)       | 190717E1       | 190717E1          | OK
Supervisor ROMMON (SUP0 Active)  | 16.7(9r)S      | 17.15(1r)S        | OK
Supervisor ROMMON (SUP1 Standby) | 16.7(9r)S      | 16.7(9r)S         | OK
Line Card CPLD (slot 0,1)        | 00000026       | 00000043          | OK
Line Card CPLD (pozostałe sloty) | 00000026       | 00000026          | OK
Gemini2 Micro (dsphy)            | 3.1A           | 3.1A              | OK
Gemini2 Apollo FPGA              | 4.484F         | 4.484F            | OK

────────────────────────────────────────────
pl-bzg01a-br06 – Wyniki weryfikacji:
────────────────────────────────────────────
pl-bzg01a-br05#terminal length 0
pl-bzg01a-br05#$i "Slot: SUP|CPLD version|Rommon version|micro|fpga"
        CPLD version                : 00000043
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000043
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 00000026
        Rommon version              : 2011.03.18
        dsphy0_micro version        : 3.1A
        dsphy1_micro version        : 3.1A
        CPLD version                : 190717E1
        ViperSO CPLD version        : 15111401
        ViperSIO CPLD version       : 15111301
        Rommon version              : 17.15(1r)S
        SUP-PIC CPLD version        : 16051301
        SUP-DC CPLD version         : 15092508
        CPLD version                : 190717E1
        ViperSO CPLD version        : 15111401
        ViperSIO CPLD version       : 15111301
        Rommon version              : 16.7(9r)S
        SUP-PIC CPLD version        : 16051301
        SUP-DC CPLD version         : 15092508
pl-bzg01a-br05#show hw-module all fpd

==== ====================== ====== =============================================
                             H/W   Field Programmable   Current   Min. Required
Slot Card Type               Ver.  Device: "ID-Name"    Version      Version
==== ====================== ====== ================== =========== ==============
 0/1 CBR-RF-PROT-PIC         5.0   35-CBR STEALTHSTAR     7.30        7.13
---- ---------------------- ------ ------------------ ----------- --------------
 1/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 2/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 3/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 4/1 CBR-2X100G-PIC          2.0   55-CBR SUPVE PIC       2.88        2.88
---- ---------------------- ------ ------------------ ----------- --------------
 5/1 CBR-2X100G-PIC          2.0   55-CBR SUPVE PIC       2.88        2.88
---- ---------------------- ------ ------------------ ----------- --------------
 6/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 7/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 8/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
---- ---------------------- ------ ------------------ ----------- --------------
 9/1 CBR-RF-PIC              4.0   34-CBR RFSW PIC        7.62        7.35
==== ====================== ====== =============================================


pl-bzg01a-br05#show platform
Chassis type: CBR-8-CCAP-CHASS

Slot      Type                State                 Insert time (ago)
--------- ------------------- --------------------- -----------------
0         CBR-CCAP-LC-40G     ok                    6w2d
0/1       CBR-RF-PROT-PIC     ok                    6w2d
1         CBR-CCAP-LC-40G     ok                    6w2d
1/1       CBR-RF-PIC          ok                    6w2d
2         CBR-CCAP-LC-40G     ok                    6w2d
2/1       CBR-RF-PIC          ok                    6w2d
3         CBR-CCAP-LC-40G     ok                    6w2d
3/1       CBR-RF-PIC          ok                    6w2d
6         CBR-CCAP-LC-40G     ok                    6w2d
6/1       CBR-RF-PIC          ok                    6w2d
7         CBR-CCAP-LC-40G     ok                    6w2d
7/1       CBR-RF-PIC          ok                    6w2d
8         CBR-CCAP-LC-40G     ok                    6w2d
8/1       CBR-RF-PIC          ok                    6w2d
9         CBR-CCAP-LC-40G     ok                    6w2d
9/1       CBR-RF-PIC          ok                    6w2d
SUP0      CBR-SUP-250G        inserted              6w2d
 R0                           ok, active
 F0                           ok, active
 4                            ok, active
 4/1      CBR-2X100G-PIC      ok                    6w2d
SUP1      CBR-SUP-250G        inserted              6w2d
 R1                           ok, standby
 F1                           ok, standby
 5                            ok, standby
 5/1      CBR-2X100G-PIC      ok                    6w2d
P0        CBR-AC-PS           ok                    6w2d
P1        CBR-AC-PS           ok                    6w2d
P2        CBR-AC-PS           ok                    6w2d
P3        CBR-AC-PS           ok                    6w2d
P4        CBR-AC-PS           ok                    6w2d
P5        CBR-AC-PS           ok                    6w2d
P10       CBR-FAN-ASSEMBLY    ok                    6w2d
P11       CBR-FAN-ASSEMBLY    ok                    6w2d
P12       CBR-FAN-ASSEMBLY    ok                    6w2d
P13       CBR-FAN-ASSEMBLY    ok                    6w2d
P14       CBR-FAN-ASSEMBLY    ok                    6w2d

Slot      CPLD Version        Rommon Version
--------- ------------------- ---------------------------------------
0         00000043            2011.03.18
1         00000043            2011.03.18
2         00000026            2011.03.18
3         00000026            2011.03.18
6         00000026            2011.03.18
7         00000026            2011.03.18
8         00000026            2011.03.18
9         00000026            2011.03.18
SUP0      190717E1            17.15(1r)S
SUP1      190717E1            16.7(9r)S

pl-bzg01a-br06#show platform diag | i fpga
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F
        dsphy0_fpga version         : 4.484F
        dsphy1_fpga version         : 4.484F

=== PORÓWNANIE FIRMWARE vs WYMAGANE MINIMUM (br06) ===

Komponent                        | Wymagane MIN   | Aktualne          | Status
---------------------------------|----------------|-------------------|--------
Supervisor CPLD (SUP-160G)       | 16052011       | 16052011          | OK
Supervisor ROMMON (SUP0 + SUP1)  | 16.7(9r)S      | 16.7(9r)S         | OK
Line Card CPLD (wszystkie sloty) | 00000026       | 00000043          | OK (nowsza)
Gemini2 Micro (dsphy)            | 3.1A           | 3.1A              | OK
Gemini2 Apollo FPGA              | 4.484F         | 4.484F            | OK

Status: OK











==================================================================================================================================================================
3. KROK 1 – BACKUP + CZYSZCZENIE DYSKU
==================================================================================================================================================================

Sprawdzenie zawartości dysków:
dir harddisk:
dir stby-harddisk:
Wykonano: pl-bzg01a-br05 [_]  pl-bzg01a-br06 [_]

! Czyszczenie starych plików
delete harddisk:cbrsup-programmable_firmware.17.06.01z1.SPA.pkg
delete harddisk:cbrsup-universalk9.17.06.01z1.SPA.bin
delete harddisk:cbrsup-programmable_firmware.16.12.01z1.SPA.pkg
delete harddisk:cbrsup-programmable_firmware.16.12.01y.SPA.pkg
delete stby-harddisk:cbrsup-programmable_firmware.17.06.01z1.SPA.pkg
delete stby-harddisk:cbrsup-universalk9.17.06.01z1.SPA.bin
delete stby-harddisk:cbrsup-programmable_firmware.16.12.01z1.SPA.pkg
delete stby-harddisk:cbrsup-programmable_firmware.16.12.01y.SPA.pkg
delete harddisk:cbrsup-programmable_firmware.16.07.01.SPA.pkg
delete harddisk:cbrsup-rp-programmable-firmware.156-2.r.SP2-ext.01.SPA.pkg
delete stby-harddisk:cbrsup-programmable_firmware.16.07.01.SPA.pkg
delete stby-harddisk:cbrsup-rp-programmable-firmware.156-2.r.SP2-ext.01.SPA.pkg

Wykonano: pl-bzg01a-br05 [x]  pl-bzg01a-br06 [x]








! Backup konfiguracji
copy run startup-config
Wykonano: pl-bzg01a-br05 [x]  pl-bzg01a-br06 [x]

pl-bzg01a-br05#copy run startup-config
Destination filename [startup-config]?
Building configuration...
[OK]

pl-bzg01a-br06#copy run startup-config
Destination filename [startup-config]?
Building configuration...
[OK]





! pl-bzg01a-br05:
copy startup-config old.run.before.upgrade.pl-bzg01a-br05.03292026_SP_to_17.12.1z4
copy old.run.before.upgrade.pl-bzg01a-br05.03292026_SP_to_17.12.1z44 ftp://monitor:v7UPC2sc@192.168.254.96


pl-bzg01a-br05#$ld.run.before.upgrade.pl-bzg01a-br05.03292026_SP_to_17.12.1z4
Destination filename [old.run.before.upgrade.pl-bzg01a-br05.03292026_SP_to_17.12.1z4]?
1016296 bytes copied in 0.187 secs (5434738 bytes/sec)
pl-bzg01a-br05#

pl-bzg01a-br05#$_SP_to_17.12.1z4 ftp://monitor:v7UPC2sc@192.168.254.96/
Address or name of remote host [192.168.254.96]?
Destination filename [old.run.before.upgrade.pl-bzg01a-br05.03292026_SP_to_17.12.1z4]?
Writing old.run.before.upgrade.pl-bzg01a-br05.03292026_SP_to_17.12.1z4 !!!!
1016296 bytes copied in 0.657 secs (1546874 bytes/sec)
pl-bzg01a-br05#

Wykonano: pl-bzg01a-br05 [x]






! pl-bzg01a-br06:
copy startup-config old.run.before.upgrade.pl-bzg01a-br06.03292026_SP_to_17.12.1z4
copy old.run.before.upgrade.pl-bzg01a-br06.03292026_SP_to_17.12.1z4 ftp://monitor:v7UPC2sc@192.168.254.96

pl-bzg01a-br06#$ld.run.before.upgrade.pl-bzg01a-br06.03292026_SP_to_17.12.1z4
Destination filename [old.run.before.upgrade.pl-bzg01a-br06.03292026_SP_to_17.12.1z4]?
939144 bytes copied in 0.156 secs (6020154 bytes/sec)

pl-bzg01a-br06#$_SP_to_17.12.1z4 ftp://monitor:v7UPC2sc@192.168.254.96
Address or name of remote host [192.168.254.96]?
Destination filename [old.run.before.upgrade.pl-bzg01a-br06.03292026_SP_to_17.12.1z4]?
Writing old.run.before.upgrade.pl-bzg01a-br06.03292026_SP_to_17.12.1z4 !!!!
939144 bytes copied in 0.276 secs (3402696 bytes/sec)


Wykonano: pl-bzg01a-br06 [x]








Pre-check przed upgrade:


terminal length 0

show platform diag | i Slot: SUP
show platform diag | i CPLD version                : 1
show platform diag | i Rommon version              : 16
show platform diag | i CPLD version                : 000000
show platform diag | i micro
show platform diag | i fpga
show hw-module all fpd
show platform

show version
show inventory

show cable modem offline

show ip route rip
show isis neighbors
show ip ospf neighbor

show interfaces port-channel 1
show interfaces port-channel 2
show interfaces port-channel 1 stats
show interfaces port-channel 2 stats

show interfaces tenGigabitEthernet 4/1/0
show interfaces tenGigabitEthernet 4/1/1
show interfaces tenGigabitEthernet 4/1/2
show interfaces tenGigabitEthernet 4/1/3
show interfaces tenGigabitEthernet 4/1/4
show interfaces tenGigabitEthernet 4/1/5
show interfaces tenGigabitEthernet 4/1/6
show interfaces tenGigabitEthernet 4/1/7

show interfaces tenGigabitEthernet 5/1/0
show interfaces tenGigabitEthernet 5/1/1
show interfaces tenGigabitEthernet 5/1/2
show interfaces tenGigabitEthernet 5/1/3
show interfaces tenGigabitEthernet 5/1/4
show interfaces tenGigabitEthernet 5/1/5
show interfaces tenGigabitEthernet 5/1/6
show interfaces tenGigabitEthernet 5/1/7

show interfaces Hu4/1/0
show interfaces Hu4/1/1
show interfaces Hu5/1/0
show interfaces Hu5/1/1

show interfaces tenGigabitEthernet 4/1/0 stats
show interfaces tenGigabitEthernet 4/1/1 stats
show interfaces tenGigabitEthernet 4/1/2 stats
show interfaces tenGigabitEthernet 4/1/3 stats
show interfaces tenGigabitEthernet 4/1/4 stats
show interfaces tenGigabitEthernet 4/1/5 stats
show interfaces tenGigabitEthernet 4/1/6 stats
show interfaces tenGigabitEthernet 4/1/7 stats

show interfaces tenGigabitEthernet 5/1/0 stats
show interfaces tenGigabitEthernet 5/1/1 stats
show interfaces tenGigabitEthernet 5/1/2 stats
show interfaces tenGigabitEthernet 5/1/3 stats
show interfaces tenGigabitEthernet 5/1/4 stats
show interfaces tenGigabitEthernet 5/1/5 stats
show interfaces tenGigabitEthernet 5/1/6 stats
show interfaces tenGigabitEthernet 5/1/7 stats

show interfaces Hu4/1/0 stats
show interfaces Hu4/1/1 stats
show interfaces Hu5/1/0 stats
show interfaces Hu5/1/1 stats

show controllers integrated-Cable 1/0/0 rf-channel 0-162
show controllers integrated-Cable 1/0/1 rf-channel 0-162
show controllers integrated-Cable 1/0/2 rf-channel 0-162
show controllers integrated-Cable 1/0/3 rf-channel 0-162
show controllers integrated-Cable 1/0/4 rf-channel 0-162
show controllers integrated-Cable 1/0/5 rf-channel 0-162
show controllers integrated-Cable 1/0/6 rf-channel 0-162
show controllers integrated-Cable 1/0/7 rf-channel 0-162

show controllers integrated-Cable 2/0/0 rf-channel 0-162
show controllers integrated-Cable 2/0/1 rf-channel 0-162
show controllers integrated-Cable 2/0/2 rf-channel 0-162
show controllers integrated-Cable 2/0/3 rf-channel 0-162
show controllers integrated-Cable 2/0/4 rf-channel 0-162
show controllers integrated-Cable 2/0/5 rf-channel 0-162
show controllers integrated-Cable 2/0/6 rf-channel 0-162
show controllers integrated-Cable 2/0/7 rf-channel 0-162

show controllers integrated-Cable 3/0/0 rf-channel 0-162
show controllers integrated-Cable 3/0/1 rf-channel 0-162
show controllers integrated-Cable 3/0/2 rf-channel 0-162
show controllers integrated-Cable 3/0/3 rf-channel 0-162
show controllers integrated-Cable 3/0/4 rf-channel 0-162
show controllers integrated-Cable 3/0/5 rf-channel 0-162
show controllers integrated-Cable 3/0/6 rf-channel 0-162
show controllers integrated-Cable 3/0/7 rf-channel 0-162

show controllers integrated-Cable 6/0/0 rf-channel 0-162
show controllers integrated-Cable 6/0/1 rf-channel 0-162
show controllers integrated-Cable 6/0/2 rf-channel 0-162
show controllers integrated-Cable 6/0/3 rf-channel 0-162
show controllers integrated-Cable 6/0/4 rf-channel 0-162
show controllers integrated-Cable 6/0/5 rf-channel 0-162
show controllers integrated-Cable 6/0/6 rf-channel 0-162
show controllers integrated-Cable 6/0/7 rf-channel 0-162

show controllers integrated-Cable 7/0/0 rf-channel 0-162
show controllers integrated-Cable 7/0/1 rf-channel 0-162
show controllers integrated-Cable 7/0/2 rf-channel 0-162
show controllers integrated-Cable 7/0/3 rf-channel 0-162
show controllers integrated-Cable 7/0/4 rf-channel 0-162
show controllers integrated-Cable 7/0/5 rf-channel 0-162
show controllers integrated-Cable 7/0/6 rf-channel 0-162
show controllers integrated-Cable 7/0/7 rf-channel 0-162

show controllers integrated-Cable 8/0/0 rf-channel 0-162
show controllers integrated-Cable 8/0/1 rf-channel 0-162
show controllers integrated-Cable 8/0/2 rf-channel 0-162
show controllers integrated-Cable 8/0/3 rf-channel 0-162
show controllers integrated-Cable 8/0/4 rf-channel 0-162
show controllers integrated-Cable 8/0/5 rf-channel 0-162
show controllers integrated-Cable 8/0/6 rf-channel 0-162
show controllers integrated-Cable 8/0/7 rf-channel 0-162

show controllers integrated-Cable 9/0/0 rf-channel 0-162
show controllers integrated-Cable 9/0/1 rf-channel 0-162
show controllers integrated-Cable 9/0/2 rf-channel 0-162
show controllers integrated-Cable 9/0/3 rf-channel 0-162
show controllers integrated-Cable 9/0/4 rf-channel 0-162
show controllers integrated-Cable 9/0/5 rf-channel 0-162
show controllers integrated-Cable 9/0/6 rf-channel 0-162
show controllers integrated-Cable 9/0/7 rf-channel 0-162

show cable modem docsis device-class summary total
show cable modem summary total

show facility-alarm status
show environment power
show platform hardware slot 0 mcu status
show platform hardware slot 1 mcu status
show platform hardware slot 2 mcu status
show platform hardware slot 3 mcu status
show platform hardware slot 4 mcu status
show platform hardware slot 5 mcu status
show redundancy
show platform
show platform diag
show environment
show redundancy linecard all
show ip mroute
show cops servers
show cable modem voice
show cable calls
show cable metering verbose
show cable licenses all
show license summary
show license usage

show cable video encryption dvb summary

show cable video encryption dvb ecmg id 1 connection
show cable video encryption dvb ecmg id 2 connection
show cable video encryption dvb ecmg id 3 connection
show cable video encryption dvb ecmg id 4 connection
show cable video encryption dvb ecmg id 5 connection
show cable video encryption dvb ecmg id 6 connection
show cable video encryption dvb ecmg id 7 connection
show cable video encryption dvb ecmg id 8 connection
show cable video encryption dvb ecmg id 9 connection
show cable video encryption dvb ecmg id 10 connection
show cable video encryption dvb ecmg id 11 connection
show cable video encryption dvb ecmg id 12 connection
show cable video encryption dvb ecmg id 13 connection
show cable video encryption dvb ecmg id 14 connection
show cable video encryption dvb ecmg id 15 connection
show cable video encryption dvb ecmg id 16 connection
show cable video encryption dvb ecmg id 17 connection
show cable video encryption dvb ecmg id 18 connection
show cable video encryption dvb ecmg id 19 connection
show cable video encryption dvb ecmg id 20 connection
show cable video encryption dvb ecmg id 21 connection

show cable video sess logical-edge-device id 1 | i ACTIVE
show cable video sess logical-edge-device id 2 | i ACTIVE
show cable video sess logical-edge-device id 3 | i ACTIVE
show cable video sess logical-edge-device id 6 | i ACTIVE
show cable video sess logical-edge-device id 7 | i ACTIVE
show cable video sess logical-edge-device id 8 | i ACTIVE
show cable video sess logical-edge-device id 9 | i ACTIVE

show cable video sess logical-edge-device id 1 summary
show cable video sess logical-edge-device id 2 summary
show cable video sess logical-edge-device id 3 summary
show cable video sess logical-edge-device id 6 summary
show cable video sess logical-edge-device id 7 summary
show cable video sess logical-edge-device id 8 summary
show cable video sess logical-edge-device id 9 summary

show cable video sess logical-edge-device id 1
show cable video sess logical-edge-device id 2
show cable video sess logical-edge-device id 3
show cable video sess logical-edge-device id 6
show cable video sess logical-edge-device id 7
show cable video sess logical-edge-device id 8
show cable video sess logical-edge-device id 9

show cable video encryption line all

show cable video logical-edge-device id 1
show cable video logical-edge-device id 2
show cable video logical-edge-device id 3
show cable video logical-edge-device id 6
show cable video logical-edge-device id 7
show cable video logical-edge-device id 8
show cable video logical-edge-device id 9

show ip route vrf 104833070-PL_VOD_BACKEND
show ip route vrf 104833072-PL_VOD_CA
show ip route vrf 104833078-PL_VOD_STREAMING

show ip route vrf 104833070-PL_VOD_BACKEND | i connected
show ip route vrf 104833072-PL_VOD_CA | i connected
show ip route vrf 104833078-PL_VOD_STREAMING | i connected

show cable l2-vpn xconnect mpls-vc-map

show cable l2-vpn xconnect mpls-vc-map customer TMO-INTERNET
show cable l2-vpn xconnect mpls-vc-map customer NTA-INTERNET
show cable l2-vpn xconnect mpls-vc-map customer VEC-INTERNET

show cable l2-vpn xconnect mpls-vc-map state | include TMO-INTERNET
show cable l2-vpn xconnect mpls-vc-map state | include NTA-INTERNET
show cable l2-vpn xconnect mpls-vc-map state | include VEC-INTERNET

show cable l2-vpn xconnect mpls-vc-map customer TMO-INTERNET | count TMO
show cable l2-vpn xconnect mpls-vc-map customer NTA-INTERNET | count NTA
show cable l2-vpn xconnect mpls-vc-map customer VEC-INTERNET | count VEC



Wykonano: pl-bzg01a-br05 [x]  pl-bzg01a-br06 [x]

────────────────────────────────────────────
pl-bzg01a-br05 – Backup wykonany / Pre-check:
────────────────────────────────────────────
PRE_03292026-pl-bzg01a-br05.txt
POST_03292026-pl-bzg01a-br05.txt
────────────────────────────────────────────
pl-bzg01a-br06 – Backup wykonany / Pre-check/Post-check:
────────────────────────────────────────────

PRE_03292026-pl-bzg01a-br06.txt











==================================================================================================================================================================
4. WERYFIKACJA PLIKÓW I MD5
==================================================================================================================================================================

verify /md5 harddisk:cbrsup-universalk9.17.12.01z4.SPA.bin
verify /md5 stby-harddisk:cbrsup-universalk9.17.12.01z4.SPA.bin




Wykonano: 

verify /md5 (harddisk:cbrsup-universalk9.17.12.01z4.SPA.bin) = e2257b800c725833b1a2f0052bc98103
verify /md5 (stby-harddisk:cbrsup-universalk9.17.12.01z4.SPA.bin) = e2257b800c725833b1a2f0052bc98103

pl-bzg01a-br05 [x]  



verify /md5 (harddisk:cbrsup-universalk9.17.12.01z4.SPA.bin) = e2257b800c725833b1a2f0052bc98103
verify /md5 (stby-harddisk:cbrsup-universalk9.17.12.01z4.SPA.bin) = e2257b800c725833b1a2f0052bc98103

pl-bzg01a-br06 [x]

Oczekiwany MD5: e2257b800c725833b1a2f0052bc98103



==================================================================================================================================================================
5. USTAWIENIE BOOT I RELOAD
==================================================================================================================================================================

configure terminal
no boot system
boot system harddisk:cbrsup-universalk9.17.12.01z4.SPA.bin
config-register 0x2102
end
write memory

show run | i boot
Wykonano: pl-bzg01a-br05 [x]  pl-bzg01a-br06 [x]

Przed reload – upewnij się, że obie konsole są otwarte!

reload
Wykonano: pl-bzg01a-br05 [x]  pl-bzg01a-br06 [x]

==================================================================================================================================================================
6. POST-CHECK (po stabilizacji ~10-15 min)
==================================================================================================================================================================

terminal length 0

show platform diag | i Slot: SUP
show platform diag | i CPLD version                : 1
show platform diag | i Rommon version              : 16
show platform diag | i CPLD version                : 000000
show platform diag | i micro
show platform diag | i fpga
show hw-module all fpd
show platform

show version
show inventory

show cable modem offline

show ip route rip
show isis neighbors
show ip ospf neighbor

show interfaces port-channel 1
show interfaces port-channel 2
show interfaces port-channel 1 stats
show interfaces port-channel 2 stats

show interfaces tenGigabitEthernet 4/1/0
show interfaces tenGigabitEthernet 4/1/1
show interfaces tenGigabitEthernet 4/1/2
show interfaces tenGigabitEthernet 4/1/3
show interfaces tenGigabitEthernet 4/1/4
show interfaces tenGigabitEthernet 4/1/5
show interfaces tenGigabitEthernet 4/1/6
show interfaces tenGigabitEthernet 4/1/7

show interfaces tenGigabitEthernet 5/1/0
show interfaces tenGigabitEthernet 5/1/1
show interfaces tenGigabitEthernet 5/1/2
show interfaces tenGigabitEthernet 5/1/3
show interfaces tenGigabitEthernet 5/1/4
show interfaces tenGigabitEthernet 5/1/5
show interfaces tenGigabitEthernet 5/1/6
show interfaces tenGigabitEthernet 5/1/7

show interfaces Hu4/1/0
show interfaces Hu4/1/1
show interfaces Hu5/1/0
show interfaces Hu5/1/1

show interfaces tenGigabitEthernet 4/1/0 stats
show interfaces tenGigabitEthernet 4/1/1 stats
show interfaces tenGigabitEthernet 4/1/2 stats
show interfaces tenGigabitEthernet 4/1/3 stats
show interfaces tenGigabitEthernet 4/1/4 stats
show interfaces tenGigabitEthernet 4/1/5 stats
show interfaces tenGigabitEthernet 4/1/6 stats
show interfaces tenGigabitEthernet 4/1/7 stats

show interfaces tenGigabitEthernet 5/1/0 stats
show interfaces tenGigabitEthernet 5/1/1 stats
show interfaces tenGigabitEthernet 5/1/2 stats
show interfaces tenGigabitEthernet 5/1/3 stats
show interfaces tenGigabitEthernet 5/1/4 stats
show interfaces tenGigabitEthernet 5/1/5 stats
show interfaces tenGigabitEthernet 5/1/6 stats
show interfaces tenGigabitEthernet 5/1/7 stats

show interfaces Hu4/1/0 stats
show interfaces Hu4/1/1 stats
show interfaces Hu5/1/0 stats
show interfaces Hu5/1/1 stats

show controllers integrated-Cable 1/0/0 rf-channel 0-162
show controllers integrated-Cable 1/0/1 rf-channel 0-162
show controllers integrated-Cable 1/0/2 rf-channel 0-162
show controllers integrated-Cable 1/0/3 rf-channel 0-162
show controllers integrated-Cable 1/0/4 rf-channel 0-162
show controllers integrated-Cable 1/0/5 rf-channel 0-162
show controllers integrated-Cable 1/0/6 rf-channel 0-162
show controllers integrated-Cable 1/0/7 rf-channel 0-162

show controllers integrated-Cable 2/0/0 rf-channel 0-162
show controllers integrated-Cable 2/0/1 rf-channel 0-162
show controllers integrated-Cable 2/0/2 rf-channel 0-162
show controllers integrated-Cable 2/0/3 rf-channel 0-162
show controllers integrated-Cable 2/0/4 rf-channel 0-162
show controllers integrated-Cable 2/0/5 rf-channel 0-162
show controllers integrated-Cable 2/0/6 rf-channel 0-162
show controllers integrated-Cable 2/0/7 rf-channel 0-162

show controllers integrated-Cable 3/0/0 rf-channel 0-162
show controllers integrated-Cable 3/0/1 rf-channel 0-162
show controllers integrated-Cable 3/0/2 rf-channel 0-162
show controllers integrated-Cable 3/0/3 rf-channel 0-162
show controllers integrated-Cable 3/0/4 rf-channel 0-162
show controllers integrated-Cable 3/0/5 rf-channel 0-162
show controllers integrated-Cable 3/0/6 rf-channel 0-162
show controllers integrated-Cable 3/0/7 rf-channel 0-162

show controllers integrated-Cable 6/0/0 rf-channel 0-162
show controllers integrated-Cable 6/0/1 rf-channel 0-162
show controllers integrated-Cable 6/0/2 rf-channel 0-162
show controllers integrated-Cable 6/0/3 rf-channel 0-162
show controllers integrated-Cable 6/0/4 rf-channel 0-162
show controllers integrated-Cable 6/0/5 rf-channel 0-162
show controllers integrated-Cable 6/0/6 rf-channel 0-162
show controllers integrated-Cable 6/0/7 rf-channel 0-162

show controllers integrated-Cable 7/0/0 rf-channel 0-162
show controllers integrated-Cable 7/0/1 rf-channel 0-162
show controllers integrated-Cable 7/0/2 rf-channel 0-162
show controllers integrated-Cable 7/0/3 rf-channel 0-162
show controllers integrated-Cable 7/0/4 rf-channel 0-162
show controllers integrated-Cable 7/0/5 rf-channel 0-162
show controllers integrated-Cable 7/0/6 rf-channel 0-162
show controllers integrated-Cable 7/0/7 rf-channel 0-162

show controllers integrated-Cable 8/0/0 rf-channel 0-162
show controllers integrated-Cable 8/0/1 rf-channel 0-162
show controllers integrated-Cable 8/0/2 rf-channel 0-162
show controllers integrated-Cable 8/0/3 rf-channel 0-162
show controllers integrated-Cable 8/0/4 rf-channel 0-162
show controllers integrated-Cable 8/0/5 rf-channel 0-162
show controllers integrated-Cable 8/0/6 rf-channel 0-162
show controllers integrated-Cable 8/0/7 rf-channel 0-162

show controllers integrated-Cable 9/0/0 rf-channel 0-162
show controllers integrated-Cable 9/0/1 rf-channel 0-162
show controllers integrated-Cable 9/0/2 rf-channel 0-162
show controllers integrated-Cable 9/0/3 rf-channel 0-162
show controllers integrated-Cable 9/0/4 rf-channel 0-162
show controllers integrated-Cable 9/0/5 rf-channel 0-162
show controllers integrated-Cable 9/0/6 rf-channel 0-162
show controllers integrated-Cable 9/0/7 rf-channel 0-162

show cable modem docsis device-class summary total
show cable modem summary total

show facility-alarm status
show environment power
show platform hardware slot 0 mcu status
show platform hardware slot 1 mcu status
show platform hardware slot 2 mcu status
show platform hardware slot 3 mcu status
show platform hardware slot 4 mcu status
show platform hardware slot 5 mcu status
show redundancy
show platform
show platform diag
show environment
show redundancy linecard all
show ip mroute
show cops servers
show cable modem voice
show cable calls
show cable metering verbose
show cable licenses all
show license summary
show license usage

show cable video encryption dvb summary

show cable video encryption dvb ecmg id 1 connection
show cable video encryption dvb ecmg id 2 connection
show cable video encryption dvb ecmg id 3 connection
show cable video encryption dvb ecmg id 4 connection
show cable video encryption dvb ecmg id 5 connection
show cable video encryption dvb ecmg id 6 connection
show cable video encryption dvb ecmg id 7 connection
show cable video encryption dvb ecmg id 8 connection
show cable video encryption dvb ecmg id 9 connection
show cable video encryption dvb ecmg id 10 connection
show cable video encryption dvb ecmg id 11 connection
show cable video encryption dvb ecmg id 12 connection
show cable video encryption dvb ecmg id 13 connection
show cable video encryption dvb ecmg id 14 connection
show cable video encryption dvb ecmg id 15 connection
show cable video encryption dvb ecmg id 16 connection
show cable video encryption dvb ecmg id 17 connection
show cable video encryption dvb ecmg id 18 connection
show cable video encryption dvb ecmg id 19 connection
show cable video encryption dvb ecmg id 20 connection
show cable video encryption dvb ecmg id 21 connection

show cable video sess logical-edge-device id 1 | i ACTIVE
show cable video sess logical-edge-device id 2 | i ACTIVE
show cable video sess logical-edge-device id 3 | i ACTIVE
show cable video sess logical-edge-device id 6 | i ACTIVE
show cable video sess logical-edge-device id 7 | i ACTIVE
show cable video sess logical-edge-device id 8 | i ACTIVE
show cable video sess logical-edge-device id 9 | i ACTIVE

show cable video sess logical-edge-device id 1 summary
show cable video sess logical-edge-device id 2 summary
show cable video sess logical-edge-device id 3 summary
show cable video sess logical-edge-device id 6 summary
show cable video sess logical-edge-device id 7 summary
show cable video sess logical-edge-device id 8 summary
show cable video sess logical-edge-device id 9 summary

show cable video sess logical-edge-device id 1
show cable video sess logical-edge-device id 2
show cable video sess logical-edge-device id 3
show cable video sess logical-edge-device id 6
show cable video sess logical-edge-device id 7
show cable video sess logical-edge-device id 8
show cable video sess logical-edge-device id 9

show cable video encryption line all

show cable video logical-edge-device id 1
show cable video logical-edge-device id 2
show cable video logical-edge-device id 3
show cable video logical-edge-device id 6
show cable video logical-edge-device id 7
show cable video logical-edge-device id 8
show cable video logical-edge-device id 9

show ip route vrf 104833070-PL_VOD_BACKEND
show ip route vrf 104833072-PL_VOD_CA
show ip route vrf 104833078-PL_VOD_STREAMING

show ip route vrf 104833070-PL_VOD_BACKEND | i connected
show ip route vrf 104833072-PL_VOD_CA | i connected
show ip route vrf 104833078-PL_VOD_STREAMING | i connected

show cable l2-vpn xconnect mpls-vc-map

show cable l2-vpn xconnect mpls-vc-map customer TMO-INTERNET
show cable l2-vpn xconnect mpls-vc-map customer NTA-INTERNET
show cable l2-vpn xconnect mpls-vc-map customer VEC-INTERNET

show cable l2-vpn xconnect mpls-vc-map state | include TMO-INTERNET
show cable l2-vpn xconnect mpls-vc-map state | include NTA-INTERNET
show cable l2-vpn xconnect mpls-vc-map state | include VEC-INTERNET

show cable l2-vpn xconnect mpls-vc-map customer TMO-INTERNET | count TMO
show cable l2-vpn xconnect mpls-vc-map customer NTA-INTERNET | count NTA
show cable l2-vpn xconnect mpls-vc-map customer VEC-INTERNET | count VEC





Alarm checki dla pl-bzg01a-br05:

pl-bzg01a-br05#show logging | i ERROR
pl-bzg01a-br05#show processes cpu sorted | ex 0.00
CPU utilization for five seconds: 13%/2%; one minute: 25%; five minutes: 33%
 PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process
  78      193751      233917        828  2.23%  9.56% 10.11%   0 IOSD ipc task
 175       28753        4353       6605  0.79%  1.03%  1.06%   0 RF Resiliency Pr
 337       25652       23778       1078  0.71%  0.73%  0.76%   0 UDLD
  79        4308       23213        185  0.47%  0.17%  0.17%   0 IOSD chasfs task
 195      270110       82200       3286  0.47%  0.46%  1.65%   0 CMTS SID mgmt ta
 133       32352      327059         98  0.47%  0.70%  0.84%   0 IOSXE-RP Punt Se
 794        3576        4386        815  0.23%  0.19%  0.18%   0 SOC_RX_1
 804        3734        4668        799  0.23%  0.20%  0.19%   0 SOC_RX_2
 928        3639        4697        774  0.23%  0.20%  0.21%   0 SOC_RX_3
 929        3177        4082        778  0.23%  0.18%  0.17%   0 SOC_RX_7
 803        2836       16686        169  0.23%  0.15%  0.14%   0 SVC_4 RX IOSD-CC
 930        3462        4355        794  0.23%  0.21%  0.21%   0 SOC_RX_6
  98        2740        2501       1095  0.23%  0.11%  0.10%   0 Environmental Mo
  15       18875       68091        277  0.23%  0.21%  0.30%   0 ARP Input
 788        2895       15811        183  0.15%  0.14%  0.14%   0 SVC_4 RX IOSD-CC
 937        2672        3408        784  0.15%  0.16%  0.15%   0 SOC_RX_0
 878        2188       90657         24  0.15%  0.12%  0.11%   0 MFIB_mrib_write
 922        2653       14423        183  0.15%  0.16%  0.15%   0 SVC_4 RX IOSD-CC
 936        2477       14493        170  0.07%  0.13%  0.15%   0 SVC_4 RX IOSD-CC
 867         888       14664         60  0.07%  0.04%  0.02%   0 OSPF-13 Hello
 862        1054       18367         57  0.07%  0.05%  0.06%   0 OSPF-33 Hello
 782        2701       14957        180  0.07%  0.14%  0.15%   0 SVC_4 RX IOSD-CC
 863        1166       20706         56  0.07%  0.05%  0.06%   0 OSPF-34 Hello
 927        2706       15860        170  0.07%  0.13%  0.15%   0 SVC_4 RX IOSD-CC
 137        1693      112663         15  0.07%  0.08%  0.08%   0 L2 LISP Punt Pro
 907        2753       17501        157  0.07%  0.11%  0.10%   0 DHCPv6 client
 868        1128       20015         56  0.07%  0.05%  0.05%   0 OSPF-11 Hello
 807       13343       68788        193  0.07%  0.13%  0.18%   0 IPv6 Input
 783        2811        3510        800  0.07%  0.12%  0.13%   0 SOC_RX_9
 292        1103       37051         29  0.07%  0.06%  0.06%   0 IGMP Input
 286        1389       17066         81  0.07%  0.07%  0.06%   0 IP Input
 284       90255       74673       1208  0.07%  0.14%  0.54%   0 IP ARP Adjacency
 279         836       36080         23  0.07%  0.03%  0.02%   0 VRRS Main thread
 459       45911       11897       3859  0.07%  0.05%  0.24%   0 SUP Trap client
 865         907       14661         61  0.07%  0.04%  0.02%   0 OSPF-12 Hello
 822        1095       15390         71  0.07%  0.05%  0.06%   0 LACP Protocol
  69       15233       18801        810  0.07%  0.48%  0.50%   0 Net Background
 917        2669       15442        172  0.07%  0.14%  0.15%   0 SVC_4 RX IOSD-CC
 350         999       62668         15  0.07%  0.03%  0.05%   0 IPAM Manager
 553         904       36079         25  0.07%  0.04%  0.02%   0 MMA DB TIMER
 139        1675      112666         14  0.07%  0.11%  0.09%   0 SIS Punt Process
 265       11756       12620        931  0.07%  0.03%  0.06%   0 CMTS MAC Timer P
 825      100088      108687        920  0.07%  0.18%  0.62%   0 DHCPD Receive
 545        1100       45884         23  0.07%  0.06%  0.06%   0 PIM Process

This command only shows processes inside the IOS daemon.
Please use 'show processes cpu platform sorted'
to show processes from the underlying operating system.


Alarm checki dla pl-bzg01a-br06:



pl-bzg01a-br06#show logging | i ERROR
pl-bzg01a-br06#show processes cpu sorted | ex 0.00
CPU utilization for five seconds: 90%/13%; one minute: 80%; five minutes: 67%
 PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process
 195       47486       17781       2670 28.23% 20.91% 10.85%   0 CMTS SID mgmt ta
 813       20019       27570        726  7.59%  7.80%  4.38%   0 DHCPD Receive
 814       10554        7209       1464  6.71%  4.97%  2.45%   0 DHCPv6 Relay
 284       17940       15362       1167  6.63%  7.02%  3.94%   0 IP ARP Adjacency
 459        8292        2344       3537  4.95%  3.60%  1.88%   0 SUP Trap client
  78       14769       26778        551  4.87%  4.29%  2.36%   0 IOSD ipc task
 314        9046       39436        229  3.19%  3.49%  2.00%   0 Dynamic Secret B
 165        8064         434      18580  2.79%  1.45%  1.19%   0 Compute load avg
 133        6827       69422         98  2.07%  2.26%  1.39%   0 IOSXE-RP Punt Se
 820        1922        3608        532  1.67%  1.19%  0.49%   0 ISIS Upd EDGE-IP
 337        6945        5926       1171  1.43%  1.29%  1.06%   0 UDLD
 376        3383       17020        198  1.35%  1.24%  0.73%   0 XDR mcast
 797        1964       12348        159  1.03%  0.86%  0.45%   0 IPv6 Input
 432         901          68      13250  1.03%  0.41%  0.20%   0 QoS stats proces
  15        3006       13304        225  1.03%  1.22%  0.68%   0 ARP Input
 313        2974       19387        153  1.03%  1.14%  0.66%   0 Dynamic Configfi
 228        2511       22302        112  0.87%  1.00%  0.56%   0 cmts_cm_state_pr
 265        1583        2286        692  0.79%  0.76%  0.37%   0 CMTS MAC Timer P
 919        4918        3887       1265  0.63%  0.39%  0.66%   0 SVC_0 RX IOSD-CC
 175        3462         751       4609  0.63%  0.83%  0.59%   0 RF Resiliency Pr
 423         977        1999        488  0.47%  0.45%  0.23%   0 IPv6 RIB Event H
  69        5259        2366       2222  0.47%  0.44%  0.55%   0 Net Background
 382        1630         171       9532  0.39%  0.14%  0.20%   0 CEF background p
 913        5080        4107       1236  0.39%  0.38%  0.66%   0 SVC_0 RX IOSD-CC
 298         223        1009        221  0.39%  0.10%  0.04%   0 SSM connection m
  98         638         707        902  0.31%  0.13%  0.10%   0 Environmental Mo
 924        4863        3837       1267  0.23%  0.40%  0.66%   0 SVC_0 RX IOSD-CC
 488         154         262        587  0.23%  0.07%  0.02%   0 AToM manager
 230         953       18219         52  0.23%  0.35%  0.21%   0 cmts_dhcp_prepro
 798         716        3773        189  0.23%  0.23%  0.15%   0 IPv6 ND
  95         262        2638         99  0.23%  0.09%  0.05%   0 cpf_process_tpQ
 896        4972        4159       1195  0.23%  0.32%  0.58%   0 SVC_0 RX IOSD-CC
 812         942       10208         92  0.15%  0.19%  0.16%   0 LACP Protocol
 790         194         745        260  0.15%  0.10%  0.03%   0 SVC_4 RX IOSD-CC
 857         454       18023         25  0.15%  0.09%  0.08%   0 MFIB_mrib_write
 131         243        2101        115  0.15%  0.11%  0.07%   0 ARP HA
 442         254        9509         26  0.15%  0.06%  0.03%   0 PIM Process
 927          96         418        229  0.07%  0.05%  0.02%   0 SVC_4 RX IOSD-CC
 929         162         213        760  0.07%  0.08%  0.04%   0 SOC_RX_3
 886         325        2060        157  0.07%  0.13%  0.07%   0 DHCPv6 client
 845         193        2993         64  0.07%  0.03%  0.02%   0 OSPF-10 Hello
 842         265        4288         61  0.07%  0.05%  0.03%   0 OSPF-32 Hello
 833         112        6674         16  0.07%  0.05%  0.02%   0 DHCPv6 Listener
 907        4996        3257       1533  0.07%  0.19%  0.61%   0 SVC_0 RX IOSD-CC
 902        5177        3352       1544  0.07%  0.21%  0.60%   0 SVC_0 RX IOSD-CC
 846         282        4211         66  0.07%  0.04%  0.04%   0 OSPF-11 Hello
 843         231        3731         61  0.07%  0.05%  0.03%   0 OSPF-33 Hello
 834        1022        2211        462  0.07%  0.03%  0.05%   0 OSPF-32 Router
 900         190         268        708  0.07%  0.08%  0.04%   0 SOC_RX_1
 894         172         231        744  0.07%  0.06%  0.03%   0 SOC_RX_8
 928         143         214        668  0.07%  0.07%  0.03%   0 SOC_RX_2
 860         169       12227         13  0.07%  0.07%  0.03%   0 MFIB_backwalk
 922          95         426        223  0.07%  0.04%  0.02%   0 SVC_4 RX IOSD-CC
 849         202        3024         66  0.07%  0.04%  0.02%   0 OSPF-13 Hello
 PID Runtime(ms)     Invoked      uSecs   5Sec   1Min   5Min TTY Process
 848         168        3023         55  0.07%  0.03%  0.01%   0 OSPF-12 Hello
 791         271         324        836  0.07%  0.05%  0.05%   0 SOC_RX_9
 916         105         462        227  0.07%  0.04%  0.02%   0 SVC_4 RX IOSD-CC
 227         131         531        246  0.07%  0.06%  0.02%   0 cmts_lease_query
 350         202       14575         13  0.07%  0.04%  0.02%   0 IPAM Manager
 296         146        6204         23  0.07%  0.04%  0.02%   0 IGMP Input
 286         239        2509         95  0.07%  0.05%  0.03%   0 IP Input
 279         208        8885         23  0.07%  0.04%  0.01%   0 VRRS Main thread
  79        1992        4457        446  0.07%  0.16%  0.21%   0 IOSD chasfs task
 911         161         212        759  0.07%  0.06%  0.03%   0 SOC_RX_6

This command only shows processes inside the IOS daemon.
Please use 'show processes cpu platform sorted'
to show processes from the underlying operating system.
