<?xml version='1.0'?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:output method="xml" encoding="utf-8" indent="yes"/>


	<xsl:template match="/">

	  <xsl:if test="EXTSD04 or EXTSD09 or EXTSD03 or EXTSD11">

	    <xsl:apply-templates/>

	  </xsl:if>



	  <xsl:if test="INVOIC01 or ORDERS01 or ZESADV01">

	    <xsl:copy-of select="."/>

	  </xsl:if>

	</xsl:template>



	<xsl:template match="/EXTSD04">

	  	<INVOIC01>

		    <xsl:for-each select="IDOC">

			  <xsl:copy-of select="."/>

			</xsl:for-each>

		</INVOIC01>

	</xsl:template>

	<xsl:template match="/EXTSD09">

	  	<ORDERS01>

		    <xsl:for-each select="IDOC">

			  <xsl:copy-of select="."/>

			</xsl:for-each>

		</ORDERS01>

	</xsl:template>

	<xsl:template match="/EXTSD03">

	  	<ZESADV01>

		    <xsl:for-each select="IDOC">

			  <xsl:copy-of select="."/>

			</xsl:for-each>

		</ZESADV01>

  </xsl:template>



	<xsl:template match="/EXTSD11">

	  	<ORDERS01>

		    <xsl:for-each select="IDOC">

			  <xsl:copy-of select="."/>

			</xsl:for-each>

		</ORDERS01>

	</xsl:template>



</xsl:stylesheet>
