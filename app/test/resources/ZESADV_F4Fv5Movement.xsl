<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:LookupClient="xalan://com.adaptris.cirrus.xml.LookupClient"
    xmlns:BusinessClient="xalan://com.adaptris.cirrus.xml.BusinessClient"
    exclude-result-prefixes="xs LookupClient" version="1.0">
    <xsl:output indent="yes"/>
    <xsl:strip-space elements="*"/>
    <xsl:param name="SOURCE_PARTNER_CODE"/>
    <xsl:param name="DESTINATION_PARTNER_CODE"/>
    <xsl:param name="ENV"/>
    <xsl:param name="CirrusConnectURL"/>
    <xsl:param name="CirrusUser"/>
    <xsl:param name="CirrusPassword"/>
    <xsl:param name="CirrusTenantCode"/>
    <xsl:param name="systemDateTime"/>
    
    <xsl:variable name="salesorderNumber">
        <xsl:value-of select="format-number(/ZESADV01/IDOC/E1EDK08/E1EDP07/VGBEL,'#')"/>
    </xsl:variable>
    
    <!-- Get all UOM lookups to ensure that we only make one HTTP request to Cirrus Hub lookup tables -->
    <xsl:variable name="UOMLookups" select="LookupClient:getLookups('UOM')"/>
    <xsl:variable name="originalOrder" select="BusinessClient:getPurchaseOrder($salesorderNumber)" />

    <xsl:template match="ZESADV01/IDOC" name="Envelope">
        <!-- Obsolete variable used to set up the connection details for the Cirrus Hub lookup API -->
        <xsl:variable name="connect"
            select="LookupClient:setConnectionDetails($CirrusConnectURL, $CirrusUser, $CirrusPassword, $CirrusTenantCode)"/>
        <xsl:variable name="businessconnect"
            select="BusinessClient:setConnectionDetails($CirrusConnectURL, $CirrusUser, $CirrusPassword, $CirrusTenantCode)"/>
        
        <Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:noNamespaceSchemaLocation="http://mappings.f4f.com/F4FXML/Schemas/v5/movement.xsd">
            <xsl:call-template name="EnvelopeHeader"/>
            <xsl:call-template name="MovementDocument"/>
            <xsl:call-template name="EnvelopeTrailer"/>
        </Envelope>
    </xsl:template>

    <xsl:template name="EnvelopeHeader">
        <EnvelopeHeader>
            <SchemaVersion>5</SchemaVersion>
            <EnvelopeCreated>
                <xsl:call-template name="formatDateTime">
                    <xsl:with-param name="date" select="EDI_DC40/CREDAT"/>
                    <xsl:with-param name="time" select="EDI_DC40/CRETIM"/>
                </xsl:call-template>
            </EnvelopeCreated>
            <EnvelopeTrackingID>
                <xsl:value-of select="E1EDK07/VBELN"/>
            </EnvelopeTrackingID>
            <EnvelopeRevisionNumber>
                <xsl:text>1</xsl:text>
            </EnvelopeRevisionNumber>
            <SourcePartnerID>
                <xsl:value-of select="$SOURCE_PARTNER_CODE"/>
            </SourcePartnerID>
            <SourceDivisionID>
                <xsl:value-of select="$SOURCE_PARTNER_CODE"/>
            </SourceDivisionID>
            <DestinationPartnerID>
                <xsl:value-of select="$DESTINATION_PARTNER_CODE"/>
            </DestinationPartnerID>
            <DestinationDivisionID>
                <xsl:value-of select="$DESTINATION_PARTNER_CODE"/>
            </DestinationDivisionID>
            <TestIndicator>
                <xsl:choose>
                    <xsl:when test="$ENV = 'live'">
                        <xsl:text>False</xsl:text>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:text>True</xsl:text>
                    </xsl:otherwise>
                </xsl:choose>
            </TestIndicator>
        </EnvelopeHeader>
    </xsl:template>

    <xsl:template name="MovementDocument">
        <MovementDocument>
            <xsl:attribute name="DocumentSequenceNumber">
                <xsl:text>1</xsl:text>
            </xsl:attribute>
            <xsl:attribute name="MessageLifecycle">
                <xsl:text>New</xsl:text>
            </xsl:attribute>
            <xsl:attribute name="MovementDocumentType">
                <xsl:text>Goods Issued Note</xsl:text>
            </xsl:attribute>
            <xsl:call-template name="DocumentHeader"/>
            <xsl:apply-templates select="E1EDK08/E1EDP07" mode="DocumentLine"/>
            <xsl:call-template name="DocumentTrailer"/>
        </MovementDocument>
    </xsl:template>

    <xsl:template name="DocumentHeader">
        <DocumentHeader>
            <xsl:attribute name="Language">
                <xsl:text>EN</xsl:text>
            </xsl:attribute>
            <xsl:attribute name="Currency">
                <xsl:text>EUR</xsl:text>
            </xsl:attribute>
            <DocumentReference>
                <xsl:attribute name="Type">
                    <xsl:text>Sales Order Number</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="AssignedBy">
                    <xsl:text>Buyer</xsl:text>
                </xsl:attribute>
                <xsl:variable name="sales_order_number" select="$originalOrder/collection/purchase-order/purchase-order-detail/sales-order-number"/>
                <xsl:choose>
                     <xsl:when test="$sales_order_number != ''">
                         <xsl:value-of select="$sales_order_number"/>
                     </xsl:when>
                     <xsl:otherwise>
                         <xsl:call-template name="remove-leading-zeros">
                             <xsl:with-param name="text" select="E1EDK08/E1EDP07/VGBEL"/>
                         </xsl:call-template>
                     </xsl:otherwise>
                </xsl:choose>                    
            </DocumentReference>
            <DocumentReference>
                <xsl:attribute name="Type">
                    <xsl:text>Delivery Note Number</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="AssignedBy">
                    <xsl:text>Supplier</xsl:text>
                </xsl:attribute>
                <xsl:value-of select="E1EDK07/VBELN"/>
            </DocumentReference>
            <DocumentDate>
                <xsl:attribute name="Type">
                    <xsl:text>Document Created</xsl:text>
                </xsl:attribute>
                <xsl:value-of select="$systemDateTime"/>
            </DocumentDate>
            <Organisation>
                <xsl:attribute name="Type">
                    <xsl:text>Supplier</xsl:text>
                </xsl:attribute>
                <Reference>
                    <xsl:attribute name="Type">
                        <xsl:text>Sales Area ID</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="AssignedBy">
                        <xsl:text>Supplier</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="Explanation">
                        <xsl:value-of select="E1EDK07/VKORG"/>
                    </xsl:attribute>
                    <xsl:value-of select="E1EDK07/VKORG"/>
                </Reference>
                <Reference>
                    <xsl:attribute name="Type">
                        <xsl:text>Distribution Channel ID</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="AssignedBy">
                        <xsl:text>Supplier</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="Explanation">
                        <xsl:value-of select="E1EDK07/VTWEG"/>
                    </xsl:attribute>
                    <xsl:value-of select="E1EDK07/VTWEG"/>
                </Reference>
            </Organisation>
            <Organisation>
                <xsl:attribute name="Type">
                    <xsl:text>Buyer</xsl:text>
                </xsl:attribute>
                <Reference>
                    <xsl:attribute name="Type">
                        <xsl:text>Account Number</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="AssignedBy">
                        <xsl:text>Supplier</xsl:text>
                    </xsl:attribute>
                    <xsl:value-of select="E1EDK07/RECIPNT_NO"/>
                </Reference>
                <Name>
                    <xsl:value-of select="E1EDK08/E1EDKA2[PARVW='AG']/NAME1"/>
                </Name>
            </Organisation>

            <MovementDetails>
                <xsl:attribute name="Phase">
                    <xsl:text>001</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="Movement">
                    <xsl:text>001</xsl:text>
                </xsl:attribute>
                <xsl:call-template name="DeliveryCollectionIndicator">
                    <xsl:with-param name="value" select="E1EDK07/INCO1"/>
                </xsl:call-template>
                <Reference>
                    <xsl:attribute name="Type">
                        <xsl:text>Route ID</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="AssignedBy">
                        <xsl:text>Supplier</xsl:text>
                    </xsl:attribute>
                    <xsl:value-of select="E1EDK07/ROUTE_BEZ"/>
                </Reference>
                <Reference>
                    <xsl:attribute name="Type">
                        <xsl:text>Loading Number</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="AssignedBy">
                        <xsl:text>Supplier</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="Explanation">
                        <xsl:text>Delivery Status</xsl:text>
                    </xsl:attribute>
                    <xsl:choose>
                        <xsl:when test="E1EDK07/Z1EDK10/WBSTK = 'A' or E1EDK07/Z1EDK10/WBSTK = 'B'">
                            <xsl:text>Planned</xsl:text>
                        </xsl:when>
                        <xsl:when test="E1EDK07/Z1EDK10/WBSTK = 'C'">Loaded</xsl:when>
                    </xsl:choose>
                </Reference>
                <Date>
                    <xsl:attribute name="Type">
                        <xsl:text>Expected Despatch Date</xsl:text>
                    </xsl:attribute>
                    <xsl:value-of select="E1EDK08/E1EDK06[IDDAT = '001']/DATUM"/>
                </Date>
                <Date>
                    <xsl:attribute name="Type">
                        <xsl:text>Actual Loading Date</xsl:text>
                    </xsl:attribute>
                    <xsl:value-of select="E1EDK08/E1EDK06[IDDAT = '035']/DATUM"/>
                </Date>
                <xsl:apply-templates select="E1EDK08/E1EDKA2[PARVW = 'WE']"
                    mode="MovementDetails_Location"/>
                <Terms>
                    <Incoterms>
                        <IncotermsCode>
                            <xsl:value-of select="E1EDK07/INCO1"/>
                        </IncotermsCode>
                        <IncotermsLocation>
                            <xsl:value-of select="E1EDK07/INCO2"/>
                        </IncotermsLocation>
                    </Incoterms>
                </Terms>
            </MovementDetails>
            <xsl:call-template name="Narrative">
                <xsl:with-param name="node" select="E1EDK08/E1EDKT3[TDID = '0012']"/>
                <xsl:with-param name="type">
                    <xsl:text>Alternative Delivery Instructions</xsl:text>
                </xsl:with-param>
            </xsl:call-template>
            <xsl:call-template name="Narrative">
                <xsl:with-param name="node" select="E1EDK08/E1EDKT3[TDID = '9000']"/>
                <xsl:with-param name="type">
                    <xsl:text>Special Instructions</xsl:text>
                </xsl:with-param>
            </xsl:call-template>
            <xsl:call-template name="Narrative">
                <xsl:with-param name="node" select="E1EDK08/E1EDKT3[TDID = '9101']"/>
                <xsl:with-param name="type">
                    <xsl:text>Delivery Instructions</xsl:text>
                </xsl:with-param>
            </xsl:call-template>
        </DocumentHeader>
    </xsl:template>

    <xsl:template name="DeliveryCollectionIndicator">
        <xsl:param name="value"/>
        <xsl:attribute name="DeliveryCollectionIndicator">
            <xsl:choose>
                <xsl:when test="$value = 'CFR'">
                    <xsl:text>Delivery</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'CIF'">
                    <xsl:text>Delivery</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'CIP'">
                    <xsl:text>Delivery</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'CPT'">
                    <xsl:text>Delivery</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'DAT'">
                    <xsl:text>Delivery</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'DAP'">
                    <xsl:text>Delivery</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'DDP'">
                    <xsl:text>Delivery</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'EXW'">
                    <xsl:text>Collection</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'FCA'">
                    <xsl:text>Collection</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'FOB'">
                    <xsl:text>Collection</xsl:text>
                </xsl:when>
                <xsl:when test="$value = 'FAS'">
                    <xsl:text>Collection</xsl:text>
                </xsl:when>
            </xsl:choose>
        </xsl:attribute>
    </xsl:template>

    <xsl:template match="E1EDK08/E1EDKA2[PARVW = 'WE']" mode="MovementDetails_Location">
        <Location>
            <xsl:attribute name="Type">
                <xsl:text>Delivery Point</xsl:text>
            </xsl:attribute>
            <Reference>
                <xsl:attribute name="Type">
                    <xsl:text>Location Code</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="AssignedBy">
                    <xsl:text>Supplier</xsl:text>
                </xsl:attribute>
                <xsl:value-of select="PARTN"/>
            </Reference>
            <Address>
                <Name>
                    <xsl:value-of select="NAME1"/>
                </Name>
                <xsl:if test="NAME2 != ''">
                    <Name>
                        <xsl:value-of select="NAME2"/>
                    </Name>
                </xsl:if>
                <xsl:if test="NAME3 != ''">
                    <Name>
                        <xsl:value-of select="NAME3"/>
                    </Name>
                </xsl:if>
                <xsl:if test="NAME4 != ''">
                    <Name>
                        <xsl:value-of select="NAME4"/>
                    </Name>
                </xsl:if>
                <xsl:if test="STRAS != ''">
                    <StreetAddress>
                        <xsl:value-of select="STRAS"/>
                    </StreetAddress>
                </xsl:if>
                <xsl:if test="STRS2 != ''">
                    <StreetAddress>
                        <xsl:value-of select="STRS2"/>
                    </StreetAddress>
                </xsl:if>
                <xsl:if test="COUNC != ''">
                    <StreetAddress>
                        <xsl:value-of select="COUNC"/>
                    </StreetAddress>
                </xsl:if>
                <xsl:if test="REGIO != ''">
                    <StreetAddress>
                        <xsl:value-of select="REGIO"/>
                    </StreetAddress>
                </xsl:if>
                <xsl:if test="ORT01 != ''">
                    <CityName>
                        <xsl:value-of select="ORT01"/>
                    </CityName>
                </xsl:if>
                <xsl:if test="PFACH != ''">
                    <PostOfficeBox>
                        <xsl:value-of select="PFACH"/>
                    </PostOfficeBox>
                </xsl:if>
                <xsl:if test="ORT02 != ''">
                    <CountyDistrictName>
                        <xsl:value-of select="ORT02"/>
                    </CountyDistrictName>
                </xsl:if>
                <xsl:if test="PSTLZ != ''">
                    <PostalCode>
                        <xsl:value-of select="PSTLZ"/>
                    </PostalCode>
                </xsl:if>
                <xsl:if test="PSTL2 != ''">
                    <PostOfficeBoxPostalCode>
                        <xsl:value-of select="PSTL2"/>
                    </PostOfficeBoxPostalCode>
                </xsl:if>
                <xsl:if test="LAND1 != ''">
                    <CountryCode>
                        <xsl:value-of select="LAND1"/>
                    </CountryCode>
                </xsl:if>
            </Address>
            <xsl:if
                test="TELF != '' or TELF2 != '' or ZE1EDKA1/TEL3 != '' or TELFX != '' or TELX1 != ''">
                <Contact>
                    <xsl:if test="TELF1 != ''">
                        <Information>
                            <xsl:attribute name="Method">
                                <xsl:text>Primary Telephone</xsl:text>
                            </xsl:attribute>
                            <xsl:value-of select="TELF1"/>
                        </Information>
                    </xsl:if>
                    <xsl:if test="TELF2 != ''">
                        <Information>
                            <xsl:attribute name="Method">
                                <xsl:text>Secondary Telephone</xsl:text>
                            </xsl:attribute>
                            <xsl:value-of select="TELF2"/>
                        </Information>
                    </xsl:if>
                    <xsl:if test="ZE1EDKA1/TEL3 != ''">
                        <Information>
                            <xsl:attribute name="Method">
                                <xsl:text>Mobile Telephone</xsl:text>
                            </xsl:attribute>
                            <xsl:value-of select="ZE1EDKA1/TEL3"/>
                        </Information>
                    </xsl:if>
                    <xsl:if test="TELFX != ''">
                        <Information>
                            <xsl:attribute name="Method">
                                <xsl:text>Facsimile</xsl:text>
                            </xsl:attribute>
                            <xsl:value-of select="TELFX"/>
                        </Information>
                    </xsl:if>
                    <xsl:if test="TELX1 != ''">
                        <Information>
                            <xsl:attribute name="Method">
                                <xsl:text>Telex</xsl:text>
                            </xsl:attribute>
                            <xsl:value-of select="TELX1"/>
                        </Information>
                    </xsl:if>
                </Contact>
            </xsl:if>
        </Location>
    </xsl:template>

    <xsl:template name="Narrative">
        <xsl:param name="node"/>
        <xsl:param name="type"/>
        <xsl:for-each select="$node/E1EDKT4/TDLINE">
            <Narrative>
                <xsl:attribute name="Type">
                    <xsl:value-of select="$type"/>
                </xsl:attribute>

                <xsl:attribute name="Sequence">
                    <xsl:value-of select="position()"/>
                </xsl:attribute>
            </Narrative>
        </xsl:for-each>
    </xsl:template>

    <xsl:template match="E1EDK08/E1EDP07" mode="DocumentLine">
        <DocumentLine>
            <xsl:attribute name="LineStatus">
                <xsl:text>New</xsl:text>
            </xsl:attribute>
            <xsl:attribute name="LineNumber">
                <xsl:value-of select="E1EDP09/POSNR"/>
            </xsl:attribute>
            <xsl:attribute name="LineCategory">
                <xsl:value-of select="E1EDP09/ZE1EDP09/PSTYV"/>
            </xsl:attribute>
            <LineReference>
                <xsl:attribute name="AssignedBy">
                    <xsl:text>Supplier</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="Type">
                    <xsl:text>Sales Order Number</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="LineNumber">
                    <xsl:value-of select="VGPOS"/>
                </xsl:attribute>
                <xsl:call-template name="remove-leading-zeros">
                    <xsl:with-param name="text" select="VGBEL"/>
                </xsl:call-template>
                
                
            </LineReference>
            <LineReference>
                <xsl:attribute name="AssignedBy">
                    <xsl:text>Buyer</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="Type">
                    <xsl:text>Purchase Order Number</xsl:text>
                </xsl:attribute>
                <xsl:if test="POSEX != ''">
                    <xsl:attribute name="LineNumber">
                        <xsl:value-of select="POSEX"/>
                    </xsl:attribute>
                </xsl:if>
                <xsl:value-of select="BSTNK"/>
            </LineReference>
            <xsl:if test="BSTDK != ''">
                <LineDate>
                    <xsl:attribute name="AssignedBy">
                        <xsl:text>Buyer</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="Type">
                        <xsl:text>Purchase Order Date</xsl:text>
                    </xsl:attribute>
                    <xsl:value-of select="BSTDK"/>
                </LineDate>
            </xsl:if>
            <MovementDetails>
                <xsl:attribute name="Phase">
                    <xsl:text>1</xsl:text>
                </xsl:attribute>
                <xsl:attribute name="Movement">
                    <xsl:text>1</xsl:text>
                </xsl:attribute>
                <xsl:call-template name="DeliveryCollectionIndicator">
                    <xsl:with-param name="value" select="../../E1EDK07/INCO1"/>
                </xsl:call-template>
                <Location>
                    <xsl:attribute name="Type">
                        <xsl:text>Storage Location</xsl:text>
                    </xsl:attribute>
                    <Reference>
                        <xsl:attribute name="Type">
                            <xsl:text>Location Code</xsl:text>
                        </xsl:attribute>
                        <xsl:attribute name="AssignedBy">
                            <xsl:text>Supplier</xsl:text>
                        </xsl:attribute>
                        <xsl:value-of select="Z1EDP00/WERKS"></xsl:value-of>
                    </Reference>
                    <Address>
                        <Name>
                            <xsl:value-of select="Z1EDP00/WERKS_BEZ"/>
                        </Name>
                    </Address>
                </Location>
            </MovementDetails>
            <LineComponent>
                <Product>
                    <Specification>
                        <Reference>
                            <xsl:attribute name="Type">
                                <xsl:text>Identifier</xsl:text>
                            </xsl:attribute>
                            <xsl:attribute name="AssignedBy">
                                <xsl:text>Supplier</xsl:text>
                            </xsl:attribute>
                            <xsl:value-of select="E1EDP09/MATNR"/>
                        </Reference>
                        <Description>
                            <xsl:attribute name="AssignedBy">
                                <xsl:text>Supplier</xsl:text>
                            </xsl:attribute>
                            <xsl:value-of select="E1EDP09/ARKTX"/>
                        </Description>
                    </Specification>                    
                    <Quantity>
                        <xsl:attribute name="Type">
                            <xsl:text>Despatched</xsl:text>
                        </xsl:attribute>
                        <xsl:attribute name="AssignedBy">
                            <xsl:text>Supplier</xsl:text>
                        </xsl:attribute>
                        <xsl:attribute name="UnitOfMeasure">
                            <xsl:call-template name="lookupUOM">
                                <xsl:with-param name="SAPUOM">
                                    <xsl:value-of select="E1EDP09/VRKME"/>
                                </xsl:with-param>
                            </xsl:call-template>
                        </xsl:attribute>
                        <xsl:value-of select="E1EDP09/LFIMG"/>
                    </Quantity>
                    <xsl:if test="Z1EDP00/WMENG != ''">
                        <Quantity>
                            <xsl:attribute name="Type">
                                <xsl:text>Ordered</xsl:text>
                            </xsl:attribute>
                            <xsl:attribute name="AssignedBy">
                                <xsl:text>Supplier</xsl:text>
                            </xsl:attribute>
                            <xsl:attribute name="UnitOfMeasure">
                                <xsl:call-template name="lookupUOM">
                                    <xsl:with-param name="SAPUOM">
                                        <xsl:value-of select="Z1EDP00/VRKME"/>
                                    </xsl:with-param>
                                </xsl:call-template>
                            </xsl:attribute>
                            <xsl:value-of select="Z1EDP00/WMENG"/>
                        </Quantity>
                    </xsl:if>
                </Product>
            </LineComponent>
            <xsl:for-each select="E1EDPT1/E1EDPT2/TDLINE">
                <Narrative>
                    <xsl:attribute name="Type">
                        <xsl:text>User Defined 1</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="Sequence">
                        <xsl:value-of select="position()"/>
                    </xsl:attribute>
                    <xsl:attribute name="Language">
                        <xsl:text>EN</xsl:text>
                    </xsl:attribute>
                    <xsl:attribute name="SendersTextCode">
                        <xsl:value-of select="../../TDID"/>
                    </xsl:attribute>
                </Narrative>
            </xsl:for-each>
        </DocumentLine>

    </xsl:template>

    <xsl:template name="DocumentTrailer">
        <DocumentTrailer>
            <Totals>
                <xsl:attribute name="TotalType">
                    <xsl:text>Control</xsl:text>
                </xsl:attribute>
                <TotalLineCount>
                    <xsl:value-of select="count(E1EDL20/E1EDL24)"/>
                </TotalLineCount>
            </Totals>
        </DocumentTrailer>
    </xsl:template>

    <xsl:template name="EnvelopeTrailer">
        <EnvelopeTrailer>
            <TotalMessageCount>1</TotalMessageCount>
        </EnvelopeTrailer>
    </xsl:template>

    <xsl:template name="formatDateTime">
        <xsl:param name="date"/>
        <xsl:param name="time"/>
        <xsl:value-of
            select="concat($date, ' ', substring($time, 1, 2), ':', substring($time, 3, 2), ':', substring($time, 5, 2))"
        />
    </xsl:template>

    <!-- UOM Lookup function that uses the cached global UOM lookups - Using this function ensures that we only make one HTTP request to Cirrus Hub lookup tables -->
    <xsl:template name="lookupUOM">
        <xsl:param name="SAPUOM"/>
        <xsl:value-of select="$UOMLookups/collection/lookup-value[key1 = $SAPUOM]/value1"/>
    </xsl:template>
    
    <xsl:template name="remove-leading-zeros">
        <xsl:param name="text"/>
        <xsl:choose>
            <xsl:when test="starts-with($text,'0')">
                <xsl:call-template name="remove-leading-zeros">
                    <xsl:with-param name="text"
                        select="substring-after($text,'0')"/>
                </xsl:call-template>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$text"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template> 

</xsl:stylesheet>


