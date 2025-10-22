from django.db import models

# Create your models here.
class PolicyMaster(models.Model):
    policymasterid = models.IntegerField(db_column='PolicyMasterID', primary_key=True)
    customerid = models.IntegerField(db_column='CustomerID')
    productid = models.IntegerField(db_column='ProductID')
    policystatusid = models.IntegerField(db_column='PolicyStatusID')
    policynumber = models.CharField(db_column='PolicyNumber', max_length=50)
    liveriskid = models.IntegerField(db_column='LiveRiskID')
    renewaldate = models.DateTimeField(db_column='RenewalDate')
    schemeid = models.IntegerField(db_column='SchemeID')
    cancellationeffectivedate = models.DateTimeField(db_column='CancellationEffectiveDate')

    class Meta:
        managed = False
        db_table = 'PolicyMaster'


class PolicyHistory(models.Model):
    policyhistoryid = models.IntegerField(db_column='PolicyHistoryID', primary_key=True)
    policymasterid = models.IntegerField(db_column='PolicyMasterID')
    riskid = models.IntegerField(db_column='RiskID') 
    adustmentnumber = models.IntegerField(db_column='AdjustmentNumber')
    creationdate = models.DateTimeField(db_column='CreationDate')
    effectivedate = models.DateTimeField(db_column='EffectiveDate')
    schemequoteresultid = models.IntegerField(db_column='SchemeQuoteResultID')
    transactiontypeid = models.IntegerField(db_column='TransactionTypeID') 
    gwp = models.FloatField(db_column='CalculatedNetPremiumExclIPT')

    class Meta:
        managed = False
        db_table = 'PolicyHistory'


class TransactionType(models.Model):
    transactiontypeid = models.IntegerField(db_column='TransactionTypeID', primary_key=True)
    trans_name = models.CharField(db_column='Name', max_length=50)  

    class Meta:
        managed = False
        db_table = 'TransactionType'


class Risk(models.Model):
    riskid = models.IntegerField(db_column='RiskID', primary_key=True)
    copay = models.IntegerField(db_column='CoinsuranceRuleID')

    class Meta:
        managed = False
        db_table = 'Risk'


class PetRates(models.Model):
    PET_CHOICES = [
        ('cat', 'Cat'),
        ('dog', 'Dog'),
    ]

    pet_type = models.CharField(max_length=10, choices=PET_CHOICES)
    scheme = models.CharField(max_length=50)  # e.g., Bronze, Silver
    factor = models.CharField(max_length=50)  # e.g., 'base_rate', 'copay', 'postcode', 'breed'
    option = models.CharField(max_length=50, null=True, blank=True)  # e.g., 'yes', 'no', 'AB'
    rate = models.FloatField()
    limit = models.FloatField(null=True, blank=True)  # e.g., 2250

    class Meta:
        unique_together = ('pet_type', 'scheme', 'factor', 'option')

    def __str__(self):
        return f"{self.pet_type} | {self.scheme} | {self.factor} | {self.option} = {self.rate}"