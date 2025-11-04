from django.db import models

# Create your models here.
class PolicyMaster(models.Model):
    policy_master_id = models.IntegerField(db_column='PolicyMasterID', primary_key=True)
    customer_id = models.IntegerField(db_column='CustomerID')
    product_id = models.IntegerField(db_column='ProductID')
    policy_status_id = models.IntegerField(db_column='PolicyStatusID')
    policy_number = models.CharField(db_column='PolicyNumber', max_length=50)
    live_risk_id = models.IntegerField(db_column='LiveRiskID')
    renewal_date = models.DateTimeField(db_column='RenewalDate')
    scheme_id = models.IntegerField(db_column='SchemeID')
    cancellation_effective_date = models.DateTimeField(db_column='CancellationEffectiveDate')

    class Meta:
        managed = False
        db_table = 'PolicyMaster'


class PolicyHistory(models.Model):
    policy_history_id = models.IntegerField(db_column='PolicyHistoryID', primary_key=True)
    policy_master_id = models.IntegerField(db_column='PolicyMasterID')
    risk_id = models.IntegerField(db_column='RiskID') 
    adustment_number = models.IntegerField(db_column='AdjustmentNumber')
    creation_date = models.DateTimeField(db_column='CreationDate')
    effective_date = models.DateTimeField(db_column='EffectiveDate')
    scheme_quote_result_id = models.IntegerField(db_column='SchemeQuoteResultID')
    transaction_type_id = models.IntegerField(db_column='TransactionTypeID') 
    gwp = models.FloatField(db_column='CalculatedNetPremiumExclIPT')

    class Meta:
        managed = False
        db_table = 'PolicyHistory'


class TransactionType(models.Model):
    transaction_type_id = models.IntegerField(db_column='TransactionTypeID', primary_key=True)
    transaction_name = models.CharField(db_column='Name', max_length=50)  

    class Meta:
        managed = False
        db_table = 'TransactionType'


class Risk(models.Model):
    risk_id = models.IntegerField(db_column='RiskID', primary_key=True)
    copay = models.IntegerField(db_column='CoinsuranceRuleID')

    class Meta:
        managed = False
        db_table = 'Risk'

class PetRiskPet(models.Model):
    pet_risk_pet_id = models.IntegerField(db_column="PetRiskPetID", primary_key=True)
    pet_type_dldid = models.IntegerField(db_column="PetTypeDLDID")
    pet_sub_type_dldid = models.IntegerField(db_column="PetSubTypeDLDID")
    breed_dldid = models.IntegerField(db_column="BreedDLDID")
    size_dldid = models.IntegerField(db_column="SizeDLDID")
    gender_dldid = models.IntegerField(db_column="GenderDLDID")
    risk_id = models.IntegerField(db_column="RiskID")
    cost_of_pet = models.IntegerField(db_column="CostofPet")
    pet_dob = models.DateField(db_column="DateofBirth")
    pet_name = models.CharField(db_column="Name", max_length=50)

    class Meta:
        managed = False
        db_table = 'PetRiskPet'

class DefinedListDetail(models.Model):
    defined_list_detail_id = models.IntegerField(db_column="DefinedListDetailID", primary_key=True)
    dld_name = models.CharField(db_column="Name", max_length=50)
    unique_id = models.CharField(db_column="UniqueID", max_length=50)

    class Meta:
        managed = False
        db_table = 'DefinedListDetail'


class PetRisk(models.Model):
    risk_id = models.IntegerField(db_column="RiskID", primary_key=True)
    pet_proposer_id = models.IntegerField(db_column="PetProposerID")
    pet_cover_level_dldid = models.IntegerField(db_column="PetCoverLevelDLDID")

    class Meta:
        managed = False
        db_table = 'PetRisk'

class PetProposer(models.Model):
    pet_proposer_id = models.IntegerField(db_column="PetProposerID", primary_key=True)
    address_id = models.IntegerField(db_column="AddressID")
    title_dldid = models.IntegerField(db_column="TitleDLDID")
    ph_dob = models.DateField(db_column="DateOfBirth")

    class Meta:
        managed = False
        db_table = 'PetProposer'

class Address(models.Model):
    address_id = models.IntegerField(db_column="AddressID", primary_key=True)
    postcode = models.CharField(db_column="PostCode", max_length=12)

    class Meta:
        managed = False
        db_table = 'Address'



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