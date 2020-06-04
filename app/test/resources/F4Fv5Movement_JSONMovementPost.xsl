<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:LookupClient="xalan://com.adaptris.cirrus.xml.LookupClient"
    exclude-result-prefixes="xs LookupClient" version="1.0">
    <xsl:output method="xml" encoding="UTF-8" indent="yes" omit-xml-declaration="no"/>
    <xsl:strip-space elements="*"/>
    <xsl:param name="ENV"/>
    <xsl:param name="CirrusConnectURL"/>
    <xsl:param name="CirrusUser"/>
    <xsl:param name="CirrusPassword"/>
    <xsl:param name="CirrusTenantCode"/>
    <!-- Get all lookups to ensure that we only make one HTTP request to Cirrus Hub lookup tables -->
    <xsl:variable name="UOMLookups" select="LookupClient:getLookups('UOM')"/>
    <xsl:variable name="LanguageLookups" select="LookupClient:getLookups('Languages')"/>


    <xsl:template match="/Envelope" name="Envelope">
        <xsl:variable name="connect"
            select="LookupClient:setConnectionDetails($CirrusConnectURL, $CirrusUser, $CirrusPassword, $CirrusTenantCode)"/>
        <o>
            <movements class="array">
                <e class="object">
                    <supplier_code type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/Organisation[@Type = 'Supplier']/Reference[@Type = 'Sales Area ID']"
                        />
                    </supplier_code>
                    <account_code type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/Organisation[@Type = 'Buyer']/Reference[@Type = 'Account Number']"
                        />
                    </account_code>
                    <account_name type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/Organisation[@Type = 'Buyer']/Name"
                        />
                    </account_name>
                    <movement_type_code type="string">
                        <xsl:text>D</xsl:text>
                    </movement_type_code>
                    <shipto_code type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Reference"
                        />
                    </shipto_code>
                    <shipto_name type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Address/Name"
                        />
                    </shipto_name>
                    <shipto_address_1 type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Address/StreetAddress"
                        />
                    </shipto_address_1>
                    <shipto_address_2 type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Address/StreetAddress[2]"
                        />
                    </shipto_address_2>
                    <shipto_address_3 type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Address/CityName"
                        />
                    </shipto_address_3>
                    <shipto_address_4 type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Address/CountyDistrictName"
                        />
                    </shipto_address_4>
                    <shipto_postcode type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Address/PostalCode"
                        />
                    </shipto_postcode>
                    <shipto_country type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/MovementDetails/Location/Address/CountryCode"
                        />
                    </shipto_country>
                    <shipfrom_name>
                        <xsl:value-of 
                            select="MovementDocument/DocumentLine/MovementDetails/Location/Address/Name"
                         />
                    </shipfrom_name>
                    <order_number type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentLine/LineReference[@Type = 'Sales Order Number'][@AssignedBy = 'Supplier']"
                        />
                    </order_number>
                    <order_date type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentLine/LineDate[@Type = 'Purchase Order Date'][@AssignedBy = 'Supplier']"
                        />
                    </order_date>

                    <supplier_movement_reference type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/DocumentReference[@Type = 'Delivery Note Number'][@AssignedBy = 'Supplier']"
                        />
                    </supplier_movement_reference>
                    <movement_date type="string">
                        <xsl:variable name="movDate" >
                            <xsl:value-of select="MovementDocument/DocumentHeader/MovementDetails/Date[@Type = 'Actual Loading Date']"/>
                        </xsl:variable>
                        <xsl:value-of
                            select="concat(substring($movDate,1,4),'-',substring($movDate,5,2),'-',substring($movDate,7,2))"
                        />
                    </movement_date>
                    <requested_delivery_date type="string">
                        <xsl:variable name="reqDate" >
                            <xsl:value-of select="MovementDocument/DocumentHeader/MovementDetails/Date[@Type = 'Expected Despatch Date']"/>
                        </xsl:variable>
                        <xsl:value-of
                            select="concat(substring($reqDate,1,4),'-',substring($reqDate,5,2),'-',substring($reqDate,7,2))"
                        />
                    </requested_delivery_date>
                    <order_code type="string">
                        <xsl:value-of
                            select="MovementDocument/DocumentHeader/DocumentReference[@Type='Sales Order Number'][@AssignedBy='Buyer']"
                        />
                    </order_code>
                    <status_code type="string">
                        <xsl:choose>
                            <xsl:when test="MovementDocument/DocumentHeader/MovementDetails/Reference[@Type='Loading Number'][@Explanation='Delivery Status']='Planned' or
                                MovementDocument/DocumentHeader/MovementDetails/Reference[@Type='Loading Number'][@Explanation='Delivery Status']=''">
                                <xsl:value-of select="'DS10'"/>
                            </xsl:when>
                            <xsl:when test="MovementDocument/DocumentHeader/MovementDetails/Reference[@Type='Loading Number'][@Explanation='Delivery Status']='Loaded'">
                                <xsl:value-of select="'DS30'"/>
                            </xsl:when>
                        </xsl:choose>
                    </status_code>
                    <movement_lines class="array">
                        <xsl:apply-templates select="MovementDocument/DocumentLine" />
                    </movement_lines>
                </e>
            </movements>
            <transaction_options class="object">
                <continue_on_fail type="boolean">false</continue_on_fail>
                <rollback_on_error type="boolean">true</rollback_on_error>
            </transaction_options>
        </o>
    </xsl:template>
    
    <xsl:template match="DocumentLine">
            
                <e class="object">
                    <order_line_number type="string">
                        <xsl:apply-templates select="@LineNumber"></xsl:apply-templates>
                    </order_line_number>
                    <product_code type="string">
                        <xsl:value-of
                            select="LineComponent/Product/Specification/Reference"/>
                    </product_code>
                    <product_description type="string">
                        <xsl:value-of
                            select="LineComponent/Product/Specification/Description"/>
                    </product_description>
                    
                    <order_qty type="string">
                        <xsl:value-of
                            select="LineComponent/Product/Quantity[@Type='Ordered']"/>
                    </order_qty>
                    <shipto_code type="string">
                        <xsl:value-of
                            select="../../MovementDocument/DocumentHeader/MovementDetails/Location/Reference"
                        />
                    </shipto_code>
                    <shipfrom_code type="string">
                        <xsl:value-of
                            select="../../MovementDocument/DocumentHeader/Organisation[@Type = 'Supplier']/Reference[@Type = 'Sales Area ID']"
                        />
                    </shipfrom_code>
                    <status_code type="string">
                        <xsl:choose>
                            <xsl:when test="../../MovementDocument/DocumentHeader/MovementDetails/Reference[@Type='Loading Number'][@Explanation='Delivery Status']='Planned' or
                                ../../MovementDocument/DocumentHeader/MovementDetails/Reference[@Type='Loading Number'][@Explanation='Delivery Status']=''">
                                <xsl:value-of select="'DL10'"/>
                            </xsl:when>
                            <xsl:when test="../../MovementDocument/DocumentHeader/MovementDetails/Reference[@Type='Loading Number'][@Explanation='Delivery Status']='Loaded'">
                                <xsl:value-of select="'DL30'"/>
                            </xsl:when>
                        </xsl:choose>
                    </status_code>
                    <despatched_qty type="string">
                        <xsl:value-of
                            select="LineComponent/Product/Quantity[@Type='Despatched']"/>                                 
                    </despatched_qty>
                    <!-- commented out 19/07/2017 ready for yara to test
					<order_uom type="string">
                        <xsl:value-of
                            select="LineComponent/Product/Quantity[@Type='Ordered']/@UnitOfMeasure"/>
                    </order_uom> -->
                    <!-- !!! New code added 19/07/2017 !!! -->
                    <order_uom>
                        <xsl:call-template name="lookupUOM">
                            <xsl:with-param name="SAPUOM" select="LineComponent/Product/Quantity[@Type='Ordered']/@UnitOfMeasure"/>
                        </xsl:call-template>
                    </order_uom>
					<!-- commented out 19/07/2017 ready for yara to test
                    <despatched_uom type="string">
                        <xsl:value-of
                            select="LineComponent/Product/Quantity[@Type='Despatched']/@UnitOfMeasure"/>
                    </despatched_uom>-->
                     <!-- !!! New code added 19/07/2017 !!! -->
                    <despatched_uom>
                        <xsl:call-template name="lookupUOM">
                            <xsl:with-param name="SAPUOM" select="LineComponent/Product/Quantity[@Type='Despatched']/@UnitOfMeasure"/>
                        </xsl:call-template>
                    </despatched_uom>
                    <line_number>
                        <xsl:value-of select="position()" />
                    </line_number>
                    </e>
            
    </xsl:template>
    
    <xsl:template name="lookupUOM">
        <xsl:param name="SAPUOM"/>
        <xsl:variable name="lookupValue"
            select="$UOMLookups/collection/lookup-value[key2 = $SAPUOM]/value2"/>
        <xsl:choose>
            <xsl:when test="$lookupValue != ''">
                <xsl:value-of select="$lookupValue"/>
            </xsl:when>
            <xsl:otherwise>
                <xsl:value-of select="$SAPUOM"/>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    
    <xsl:template match="@LineNumber">
        <xsl:value-of select="number(.)"/>
    </xsl:template>

</xsl:stylesheet>
